import argparse
import os
from app import create_app, db
from app.models import User, FocusSession, ActivityLog, FocusRoom, followers, room_participants

def delete_user(user_id=None, email=None, username=None):
    """
    ID、メールアドレス、またはユーザー名で指定されたユーザーを削除します。
    """
    # 環境変数FLASK_APPを設定
    os.environ['FLASK_APP'] = 'run.py'
    app = create_app()
    with app.app_context():
        user_to_delete = None
        if user_id:
            user_to_delete = User.query.get(user_id)
            if not user_to_delete:
                print(f"エラー: ID '{user_id}' のユーザーは見つかりませんでした。")
                return
        elif email:
            user_to_delete = User.query.filter_by(email=email).first()
            if not user_to_delete:
                print(f"エラー: メールアドレス '{email}' のユーザーは見つかりませんでした。")
                return
        elif username:
            user_to_delete = User.query.filter_by(username=username).first()
            if not user_to_delete:
                print(f"エラー: ユーザー名 '{username}' のユーザーは見つかりませんでした。")
                return

        if user_to_delete:
            deleted_user_name = user_to_delete.username
            
            # 関連データの削除
            FocusSession.query.filter_by(user_id=user_to_delete.id).delete()
            ActivityLog.query.filter_by(user_id=user_to_delete.id).delete()
            FocusRoom.query.filter_by(owner_id=user_to_delete.id).delete()

            # フォロー関係の削除 (自分がフォローしている、自分をフォローしている)
            db.session.execute(followers.delete().where(followers.c.follower_id == user_to_delete.id))
            db.session.execute(followers.delete().where(followers.c.followed_id == user_to_delete.id))

            # 参加しているルームからの削除
            db.session.execute(room_participants.delete().where(room_participants.c.user_id == user_to_delete.id))

            db.session.delete(user_to_delete)
            db.session.commit()
            print(f"ユーザー '{deleted_user_name}' を正常に削除しました。")
        else:
            print("エラー: 削除するユーザーのID、メールアドレス、またはユーザー名を指定してください。")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='データベースからユーザーを削除します。')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--id', type=int, help='削除するユーザーのID')
    group.add_argument('--email', type=str, help='削除するユーザーのメールアドレス')
    group.add_argument('--username', type=str, help='削除するユーザーのユーザー名')

    args = parser.parse_args()
    delete_user(user_id=args.id, email=args.email, username=args.username)