"""Punto de entrada: lanza la aplicación web Flask."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.routes import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    print(f"PayFlex Sales — http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
