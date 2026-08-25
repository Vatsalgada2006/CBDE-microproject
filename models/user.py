class User:
    def __init__(self, uid, email, display_name=None, photo_url=None, role='user'):
        self.uid = uid
        self.email = email
        self.display_name = display_name
        self.photo_url = photo_url
        self.role = role  # 'admin', 'manager', 'user'

    def to_dict(self):
        return {
            'uid': self.uid,
            'email': self.email,
            'display_name': self.display_name,
            'photo_url': self.photo_url,
            'role': self.role
        }

    @staticmethod
    def from_dict(data):
        return User(
            uid=data.get('uid'),
            email=data.get('email'),
            display_name=data.get('display_name'),
            photo_url=data.get('photo_url'),
            role=data.get('role', 'user')
        )
