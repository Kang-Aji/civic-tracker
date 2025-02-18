from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class OfficialAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    official_name = db.Column(db.String(200), nullable=False)
    office = db.Column(db.String(200), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    source_url = db.Column(db.String(500))
    source_type = db.Column(db.String(50))  # 'congress_api', 'news', 'press_release', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'official_name': self.official_name,
            'office': self.office,
            'action_type': self.action_type,
            'description': self.description,
            'date': self.date.isoformat(),
            'source_url': self.source_url,
            'source_type': self.source_type,
            'created_at': self.created_at.isoformat()
        }

class ActionSource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    official_name = db.Column(db.String(200), nullable=False)
    source_type = db.Column(db.String(50), nullable=False)  # 'rss', 'website', 'api'
    source_url = db.Column(db.String(500), nullable=False)
    last_checked = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'official_name': self.official_name,
            'source_type': self.source_type,
            'source_url': self.source_url,
            'last_checked': self.last_checked.isoformat() if self.last_checked else None,
            'created_at': self.created_at.isoformat()
        }
