
import os
from app import create_app, db
from app.models import User

def list_users():
    """
    すべてのユーザーを一覧表示します。
    """
    # 環境変数FLASK_APPを設定
    os.environ['FLASK_APP'] = 'run.py'
    app = create_app()
    with app.app_context():
        users = User.query.all()
        if not users:
            print("現在、ユーザーは存在しません。")
            return

        print("--- ユーザー一覧 ---")
        for user in users:
            print(f"ID: {user.id}, ユーザー名: {user.username}, メールアドレス: {user.email}")
        print("---------------------")

        # 合計ユーザー数表示（新機能）
        print(f"合計ユーザー数: {len(users)}")

if __name__ == '__main__':
    list_users()
