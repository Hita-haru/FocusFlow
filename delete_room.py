
import argparse
import os
from app import create_app, db
from app.models import FocusRoom

def delete_room(room_id=None, room_name=None):
    """
    IDまたは名前で指定されたフォーカスルームを削除します。
    """
    # 環境変数FLASK_APPを設定
    os.environ['FLASK_APP'] = 'run.py'
    app = create_app()
    with app.app_context():
        room_to_delete = None
        if room_id:
            room_to_delete = FocusRoom.query.get(room_id)
            if not room_to_delete:
                print(f"エラー: ID '{room_id}' のルームは見つかりませんでした。")
                return
        elif room_name:
            room_to_delete = FocusRoom.query.filter_by(name=room_name).first()
            if not room_to_delete:
                print(f"エラー: 名前 '{room_name}' のルームは見つかりませんでした。")
                return

        if room_to_delete:
            deleted_room_name = room_to_delete.name
            db.session.delete(room_to_delete)
            db.session.commit()
            print(f"ルーム '{deleted_room_name}' を正常に削除しました。")
        else:
            print("エラー: 削除するルームのIDまたは名前を指定してください。")
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='データベースからフォーカスルームを削除します。')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--id', type=int, help='削除するルームのID')
    group.add_argument('--name', type=str, help='削除するルームの名前')

    args = parser.parse_args()
    delete_room(room_id=args.id, room_name=args.name)
