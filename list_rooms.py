
import os
from app import create_app, db
from app.models import FocusRoom

def list_rooms():
    """
    すべてのフォーカスルームを一覧表示します。
    """
    # 環境変数FLASK_APPを設定
    os.environ['FLASK_APP'] = 'run.py'
    app = create_app()
    with app.app_context():
        rooms = FocusRoom.query.all()
        if not rooms:
            print("現在、ルームは存在しません。")
            return

        print("--- フォーカスルーム一覧 ---")
        for room in rooms:
            print(f"ID: {room.id}, 名前: {room.name}, オーナー: {room.owner.username}, 公開: {room.is_public}")
        print("--------------------------")

if __name__ == '__main__':
    list_rooms()
