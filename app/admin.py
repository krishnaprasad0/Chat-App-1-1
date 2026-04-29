from sqladmin import Admin, ModelView
from app.models.user import User
from app.models.message import Message

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.created_at]
    column_searchable_list = [User.username]
    column_sortable_list = [User.created_at]
    icon = "fa-solid fa-user"

class MessageAdmin(ModelView, model=Message):
    column_list = [
        Message.id, 
        Message.sender_id, 
        Message.receiver_id, 
        Message.message_type, 
        Message.status, 
        Message.created_at
    ]
    column_searchable_list = [Message.sender_id, Message.receiver_id]
    column_sortable_list = [Message.created_at]
    icon = "fa-solid fa-envelope"

def setup_admin(app, engine):
    admin = Admin(app, engine)
    admin.add_view(UserAdmin)
    admin.add_view(MessageAdmin)
