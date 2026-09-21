#!/usr/bin/env python3
"""Project-scoped Linear commands. Python standard library; no generic API passthrough."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

ROOT = Path(__file__).resolve().parent.parent
ENDPOINT = "https://api.linear.app/graphql"
FIELDS = """id identifier title description url priority
    team { id name key } project { id name }
    state { id name type } parent { id identifier } labels { nodes { id name } }"""
OPERATIONS = {
    "teams": "query($after:String){teams(first:100,after:$after){nodes{id name key} pageInfo{hasNextPage endCursor}}}",
    "projects": "query($after:String){projects(first:100,after:$after){nodes{id name teams{nodes{id}}} pageInfo{hasNextPage endCursor}}}",
    "scope": "query($team:String!,$project:String!){team(id:$team){id name key} project(id:$project){id name teams{nodes{id}}}}",
    "states": "query($team:ID!,$after:String){workflowStates(first:100,after:$after,filter:{team:{id:{eq:$team}}}){nodes{id name type} pageInfo{hasNextPage endCursor}}}",
    "labels": "query($after:String){issueLabels(first:100,after:$after){nodes{id name team{id}} pageInfo{hasNextPage endCursor}}}",
    "list": "query($filter:IssueFilter,$after:String,$archived:Boolean!){issues(first:100,after:$after,includeArchived:$archived,filter:$filter){nodes{" + FIELDS + "} pageInfo{hasNextPage endCursor}}}",
    "get": "query($id:String!){issue(id:$id){" + FIELDS + " comments(first:50){nodes{id body} pageInfo{hasNextPage endCursor}}}}",
    "create": "mutation($input:IssueCreateInput!){issueCreate(input:$input){success issue{id}}}",
    "update": "mutation($id:String!,$input:IssueUpdateInput!){issueUpdate(id:$id,input:$input){success issue{id}}}",
    "comment": "mutation($input:CommentCreateInput!){commentCreate(input:$input){success comment{id}}}",
    "read_comment": "query($id:String!){comment(id:$id){id body issue{id}}}",
}


class LinearError(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LinearError("APIのリダイレクトを拒否しました")


def load_token():
    token = os.environ.get("LINEAR_API_KEY", "").strip()
    if not token:
        token_file = Path.home() / ".linear_token"
        if token_file.is_file():
            token = next((s.strip() for s in token_file.read_text().splitlines() if s.strip()), "")
            token = re.sub(r"^(?:export\s+)?LINEAR_API_KEY=", "", token)
            if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
                token = token[1:-1]
    if not token or any(c.isspace() for c in token):
        raise LinearError("LINEAR_API_KEYまたはユーザー領域の.linear_tokenにAPIキーを設定してください")
    return token


def request(operation, variables):
    # No caller-provided GraphQL. Reject unknown operations before reading credentials.
    if operation not in OPERATIONS:
        raise LinearError("許可されていない操作です。Issue削除と任意GraphQLは提供しません")
    req = Request(ENDPOINT, data=json.dumps({"query": OPERATIONS[operation], "variables": variables}).encode(),
                  headers={"Authorization": load_token(), "Content-Type": "application/json"}, method="POST")
    try:
        with build_opener(NoRedirect()).open(req, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise LinearError(f"Linear HTTP {exc.code}。自動再送しません。書込時は現在値を確認してください") from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise LinearError("Linear通信またはJSON読取に失敗。書込結果は未確認です。再送前に現在値を確認してください") from None
    if not isinstance(payload, dict) or payload.get("errors") or not isinstance(payload.get("data"), dict):
        # Avoid leaking request contents or secrets through upstream error messages.
        raise LinearError("Linear APIエラー。認証・権限・指定IDを確認してください。書込は自動再送しません")
    return payload["data"]


def pages(operation, field, variables=None):
    nodes, cursor, seen = [], None, set()
    while True:
        data = request(operation, dict(variables or {}, after=cursor))
        connection = data.get(field)
        if not isinstance(connection, dict) or not isinstance(connection.get("nodes"), list):
            raise LinearError("一覧を取得できませんでした（0件とは判定しません）")
        nodes.extend(connection["nodes"])
        info = connection.get("pageInfo", {})
        if info.get("hasNextPage") is False:
            return nodes
        cursor = info.get("endCursor")
        if not cursor or cursor in seen:
            raise LinearError("ページ情報が不正です。一覧は未取得部分があります")
        seen.add(cursor)


def validate_config(config):
    if not isinstance(config, dict) or set(config) != {"teamId", "projectId"}:
        raise LinearError("設定にはteamIdとprojectIdだけを指定してください。Tokenは保存しません")
    for value in config.values():
        try:
            UUID(value)
        except (ValueError, TypeError, AttributeError):
            raise LinearError("teamId/projectIdには実在するUUIDを指定してください") from None
    return config


def load_config(root=ROOT):
    try:
        return validate_config(json.loads((root / ".linear.json").read_text()))
    except FileNotFoundError:
        raise LinearError("未設定です。discoverでIDを確認し、init --team-id UUID --project-id UUID を実行してください") from None
    except (ValueError, OSError):
        raise LinearError(".linear.jsonを読み取れません") from None


def verify_scope(config):
    data = request("scope", {"team": config["teamId"], "project": config["projectId"]})
    team, project = data.get("team"), data.get("project")
    if (not team or not project or team["id"] != config["teamId"] or project["id"] != config["projectId"]
            or config["teamId"] not in [t["id"] for t in project["teams"]["nodes"]]):
        raise LinearError("TeamとProjectの所属が一致しません")
    return data


def initialize(team_id, project_id, root=ROOT):
    config = validate_config({"teamId": team_id, "projectId": project_id})
    path = root / ".linear.json"
    if path.exists() or path.is_symlink():
        raise LinearError(".linear.jsonは既にあります。既存の設定を上書きしません")
    data = verify_scope(config)
    with path.open("x") as stream:
        json.dump(config, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return {"configured": str(path), **data}


def get_issue(identifier, config):
    issue = request("get", {"id": identifier}).get("issue")
    if (not issue or (issue.get("team") or {}).get("id") != config["teamId"]
            or (issue.get("project") or {}).get("id") != config["projectId"]):
        raise LinearError("対象Issueは設定されたTeam/Projectに属していません（書込前に停止）")
    return issue


def lookup_state(name, config):
    states = pages("states", "workflowStates", {"team": config["teamId"]})
    matches = [s for s in states if s["name"].casefold() == name.casefold()]
    if len(matches) != 1:
        raise LinearError("状態名を一意に解決できません。doctorで確認してください")
    return matches[0]


def text_value(args, name):
    value = getattr(args, name, None)
    path = getattr(args, name + "_file", None)
    if path:
        value = Path(path).read_text()
    if value is not None and not value.strip():
        raise LinearError(f"{name}は空にできません")
    return value


def write_issue(operation, fields, config, identifier=None):
    variables = {"input": fields}
    if identifier:
        variables["id"] = identifier
    data = request(operation, variables).get("issue" + operation.capitalize())
    if not data or data.get("success") is not True or not (data.get("issue") or {}).get("id"):
        raise LinearError("書込成功を確認できません。再試行前に対象を取得してください")
    readback = get_issue(data["issue"]["id"], config)
    for key, value in fields.items():
        actual = readback.get(key)
        if key in {"stateId", "parentId", "teamId", "projectId"}:
            actual = (readback.get(key[:-2]) or {}).get("id")
        # Linear normalizes Markdown; return the full readback for content review.
        if key == "labelIds":
            actual = sorted(n["id"] for n in readback["labels"]["nodes"])
            value = sorted(value)
        if key != "description" and actual != value:
            raise LinearError(f"書込後の{key}が一致しません。再送せず対象を確認してください")
    return {"success": True, "readBack": readback}


def add_comment(identifier, body, config):
    issue = get_issue(identifier, config)
    data = request("comment", {"input": {"issueId": issue["id"], "body": body}}).get("commentCreate")
    if not data or data.get("success") is not True or not (data.get("comment") or {}).get("id"):
        raise LinearError("コメント作成結果が未確認です。再送前に対象を確認してください")
    comment = request("read_comment", {"id": data["comment"]["id"]}).get("comment")
    if not comment or comment["issue"]["id"] != issue["id"] or not comment.get("body"):
        raise LinearError("作成コメントを読み戻せません。再送せず確認してください")
    return {"success": True, "commentReadBack": comment, "readBack": get_issue(issue["id"], config)}


def issue_fields(args, config):
    fields = {}
    for key in ("title", "priority"):
        value = getattr(args, key, None)
        if value is not None:
            if key == "title" and not value.strip():
                raise LinearError("titleは空にできません")
            fields[key] = value
    description = text_value(args, "description")
    if description is not None:
        fields["description"] = description
    if args.state:
        state = lookup_state(args.state, config)
        if state["type"] in {"canceled", "duplicate"}:
            raise LinearError("取消・重複状態へ移す場合はcancel --reasonを使ってください")
        fields["stateId"] = state["id"]
    if args.parent:
        fields["parentId"] = get_issue(args.parent, config)["id"]
    if args.label:
        matches = [n for n in pages("labels", "issueLabels") if n["name"] == args.label
                   and (not n.get("team") or n["team"]["id"] == config["teamId"])]
        if len(matches) != 1:
            raise LinearError("ラベルを一意に解決できません")
        fields["labelIds"] = [matches[0]["id"]]
    return fields


def parser():
    cli = argparse.ArgumentParser(description="Project設定を使うLinear CLI。削除操作なし。")
    commands = cli.add_subparsers(dest="command", required=True)
    commands.add_parser("discover", help="利用可能なTeam/ProjectのIDを読み取る")
    init = commands.add_parser("init", help="既存Team/Projectに接続（外部作成なし）")
    init.add_argument("--team-id", required=True)
    init.add_argument("--project-id", required=True)
    commands.add_parser("doctor", help="現在の設定・所属・状態名を確認")
    listing = commands.add_parser("list", help="完了・アーカイブ含む全ページ取得")
    listing.add_argument("--state")
    listing.add_argument("--active-only", action="store_true", help="アーカイブを除く")
    commands.add_parser("get").add_argument("--id", required=True)
    for verb in ("create", "update"):
        sub = commands.add_parser(verb)
        if verb == "update":
            sub.add_argument("--id", required=True)
        sub.add_argument("--title", required=verb == "create")
        sub.add_argument("--state", default="Todo" if verb == "create" else None)
        sub.add_argument("--priority", type=int, choices=range(5))
        sub.add_argument("--parent")
        sub.add_argument("--label")
        description = sub.add_mutually_exclusive_group()
        description.add_argument("--description")
        description.add_argument("--description-file")
    comment = commands.add_parser("comment")
    comment.add_argument("--id", "--issue-id", dest="id", required=True)
    body = comment.add_mutually_exclusive_group(required=True)
    body.add_argument("--body")
    body.add_argument("--body-file")
    cancel = commands.add_parser("cancel")
    cancel.add_argument("--id", required=True)
    cancel.add_argument("--reason", required=True)
    cancel.add_argument("--state", default="Canceled")
    return cli


def execute(args, root=ROOT):
    if args.command == "discover":
        return {"teams": pages("teams", "teams"), "projects": pages("projects", "projects")}
    if args.command == "init":
        return initialize(args.team_id, args.project_id, root)
    config = load_config(root)
    if args.command == "doctor":
        return {"ok": True, **verify_scope(config), "states": pages("states", "workflowStates", {"team": config["teamId"]}), "deleteCommand": False}
    if args.command == "list":
        verify_scope(config)
        filters = {"team": {"id": {"eq": config["teamId"]}}, "project": {"id": {"eq": config["projectId"]}}}
        if args.state:
            filters["state"] = {"id": {"eq": lookup_state(args.state, config)["id"]}}
        issues = pages("list", "issues", {"filter": filters, "archived": not args.active_only})
        return {"issues": issues, "count": len(issues), "hasNextPage": False}
    if args.command == "get":
        return get_issue(args.id, config)
    if args.command == "create":
        verify_scope(config)
        return write_issue("create", dict(issue_fields(args, config), **config), config)
    if args.command == "update":
        issue = get_issue(args.id, config)
        fields = issue_fields(args, config)
        if not fields:
            raise LinearError("更新する項目を指定してください")
        if fields.get("parentId") == issue["id"]:
            raise LinearError("自分自身を親Issueにできません")
        return write_issue("update", fields, config, issue["id"])
    if args.command == "comment":
        return add_comment(args.id, text_value(args, "body"), config)
    if args.command == "cancel":
        if not args.reason.strip():
            raise LinearError("取消理由は空にできません")
        issue = get_issue(args.id, config)
        state = lookup_state(args.state, config)
        if state["type"] not in {"canceled", "duplicate"}:
            raise LinearError("取消先にはcanceled/duplicate型の状態だけを使えます")
        if issue["state"]["id"] == state["id"]:
            return {"alreadyCanceled": True, "readBack": issue}
        comment = add_comment(args.id, "Canceled理由: " + args.reason, config)
        return {"comment": comment, **write_issue("update", {"stateId": state["id"]}, config, issue["id"])}
    raise LinearError("許可されていない操作です")


def main():
    # Reject even with missing config/credentials and do not contact the API.
    if len(sys.argv) > 1 and sys.argv[1].lower() in {"delete", "remove", "purge", "issuedelete"}:
        print("ERROR: IssueのAPI削除は禁止です。理由を残してcancelしてください。", file=sys.stderr)
        return 64
    args = parser().parse_args()
    try:
        print(json.dumps(execute(args), ensure_ascii=False, indent=2))
        return 0
    except (LinearError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
