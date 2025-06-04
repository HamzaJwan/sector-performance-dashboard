from flask import Flask
from routes.dashboard import dashboard_bp
from routes.reports import reports_bp
from routes.actions import actions_bp
from routes.admin import admin_bp
import logger  # لتهيئة اللوج

# إنشاء التطبيق
app = Flask(__name__)
app.secret_key = 'super-secret-key-2025'  # ✅ ضروري لتفعيل flash() والجلسات

# تسجيل المسارات (Blueprints)
app.register_blueprint(dashboard_bp)
app.register_blueprint(actions_bp)
app.register_blueprint(reports_bp, url_prefix='/reports')
app.register_blueprint(admin_bp, url_prefix='/admin')

# بدء التطبيق
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
