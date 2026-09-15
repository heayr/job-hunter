import json
import os
import sqlite3
import sys
import glob
import re
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler

# Auto-inject virtual environment packages
venv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.venv')
if os.path.exists(venv_path):
    site_packages = glob.glob(os.path.join(venv_path, 'lib', 'python*', 'site-packages'))
    if site_packages:
        sys.path.insert(0, site_packages[0])

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")


def simple_markdown_to_html(md_text: str) -> str:
    html = md_text.replace("<", "&lt;").replace(">", "&gt;")
    html = re.sub(r'(?m)^### (.*?)$', r'<h3>\1</h3>', html)
    html = re.sub(r'(?m)^## (.*?)$', r'<h2>\1</h2>', html)
    html = re.sub(r'(?m)^# (.*?)$', r'<h1>\1</h1>', html)
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2" target="_blank">\1</a>', html)
    html = html.replace('• ', '<br>&#8226; ')
    html = html.replace('\n', '<br>')
    html = re.sub(r'(<br>\s*){3,}', '<br><br>', html)
    return html


def _send_json(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type')
    handler.end_headers()
    handler.wfile.write(body)


class CRMHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Log only errors (4xx/5xx)
        if args and len(args) >= 2 and str(args[1]).startswith(('4', '5')):
            print(f"[CRM] {self.address_string()} - {format % args}")

    # ─────────────────────────────────────────────
    #  DB helpers
    # ─────────────────────────────────────────────

    def get_vacancies(self):
        """
        Returns all vacancies with their pitches.
        LEFT JOIN ensures vacancies without pitches are still returned.
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('''
            SELECT
                v.id, v.title, v.company, v.url, v.salary, v.location,
                v.source, v.description, v.contact_handle, v.contact_type,
                v.status, v.score,
                COALESCE(v.language, p.language, 'ru') AS language,
                MAX(CASE WHEN p.pitch_type = 'short_dm'     THEN p.content END) AS short_dm,
                MAX(CASE WHEN p.pitch_type = 'cover_letter' THEN p.content END) AS cover_letter,
                MAX(CASE WHEN p.pitch_type = 'tailored_cv'  THEN p.content END) AS tailored_cv
            FROM vacancies v
            LEFT JOIN pitches p ON p.vacancy_id = v.id
            WHERE v.status != 'archive'
            GROUP BY v.id
            ORDER BY v.created_at DESC
        ''')
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_cv(self, vac_id):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT content FROM pitches WHERE vacancy_id = ? AND pitch_type = 'tailored_cv'", (vac_id,))
        row = cur.fetchone()
        conn.close()
        return row['content'] if row else None

    def update_vacancy_status(self, vac_id, status):
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE vacancies SET status = ? WHERE id = ?", (status, vac_id))
        conn.commit()
        conn.close()

    def upsert_pitch(self, cur, vac_id, pitch_type, lang, content):
        """INSERT or UPDATE a pitch row (handles both new and existing pitches)."""
        cur.execute('''
            INSERT INTO pitches (vacancy_id, pitch_type, language, content)
            VALUES (?, ?, ?, ?)
            ON CONFLICT DO NOTHING
        ''', (vac_id, pitch_type, lang, content))
        if cur.rowcount == 0:
            cur.execute('''
                UPDATE pitches SET content = ? WHERE vacancy_id = ? AND pitch_type = ?
            ''', (content, vac_id, pitch_type))

    # ─────────────────────────────────────────────
    #  CORS preflight
    # ─────────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    # ─────────────────────────────────────────────
    #  GET routes
    # ─────────────────────────────────────────────

    def do_GET(self):
        try:
            self._handle_get()
        except Exception as e:
            import traceback
            traceback.print_exc()
            _send_json(self, {"error": str(e)}, status=500)

    def _handle_get(self):
        if self.path == '/':
            tmpl_path = os.path.join(os.path.dirname(__file__), "crm_v2_template.html")
            with open(tmpl_path, "r", encoding="utf-8") as f:
                body = f.read().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif self.path == '/api/pitches':
            data = self.get_vacancies()
            _send_json(self, data)

        elif self.path == '/api/profiles':
            profiles_path = os.path.join(os.path.dirname(__file__), 'generator', 'profiles.json')
            data = []
            if os.path.exists(profiles_path):
                with open(profiles_path, 'r', encoding='utf-8') as pf:
                    try:
                        data = json.load(pf)
                    except Exception:
                        data = []
            _send_json(self, data)

        elif self.path == '/api/config':
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as cf:
                    try:
                        config = json.load(cf)
                    except Exception:
                        pass
            _send_json(self, config)

        elif self.path.startswith('/cv/'):
            vac_id = urllib.parse.unquote(self.path[4:])
            md_cv = self.get_cv(vac_id)
            if not md_cv:
                self.send_response(404)
                self.end_headers()
                return
            html_cv = (
                '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Tailored CV</title>'
                '<style>body{font-family:sans-serif;padding:40px;line-height:1.7;color:#222;max-width:820px;margin:auto}</style>'
                f'</head><body>{simple_markdown_to_html(md_cv)}</body></html>'
            )
            body = html_cv.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()

    # ─────────────────────────────────────────────
    #  POST routes
    # ─────────────────────────────────────────────

    def do_POST(self):
        try:
            self._handle_post()
        except Exception as e:
            import traceback
            traceback.print_exc()
            _send_json(self, {"success": False, "error": str(e)}, status=500)

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(length)

    def _handle_post(self):
        # ── Rewrite vacancy pitches via AI ──
        if self.path.startswith('/api/vacancies/') and self.path.endswith('/rewrite'):
            from generator.pitch_builder import generate_pitch
            vac_id = urllib.parse.unquote(self.path.split('/')[3])

            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM vacancies WHERE id = ?", (vac_id,))
            row = cur.fetchone()
            if not row:
                conn.close()
                self.send_response(404)
                self.end_headers()
                return

            v_dict = dict(row)
            pitch_data = generate_pitch(v_dict, use_ai=True)

            self.upsert_pitch(cur, vac_id, 'short_dm',     pitch_data['language'], pitch_data['short_dm'])
            self.upsert_pitch(cur, vac_id, 'cover_letter', pitch_data['language'], pitch_data['cover_letter'])
            self.upsert_pitch(cur, vac_id, 'tailored_cv',  pitch_data['language'], pitch_data['tailored_cv'])

            # Always save score (even 0)
            score = pitch_data.get('score')
            if score is not None:
                cur.execute("UPDATE vacancies SET score = ? WHERE id = ?", (score, vac_id))

            conn.commit()
            conn.close()
            _send_json(self, {
                "success": pitch_data.get("ai_generated", False),
                "error": pitch_data.get("ai_error"),
                "short_dm": pitch_data['short_dm'],
                "cover_letter": pitch_data['cover_letter'],
                "score": pitch_data.get('score', 0),
            })

        # ── Update vacancy status ──
        elif self.path.startswith('/api/vacancies/') and self.path.endswith('/status'):
            vac_id = urllib.parse.unquote(self.path.split('/')[3])
            body = json.loads(self._read_body().decode('utf-8'))
            self.update_vacancy_status(vac_id, body.get('status'))
            _send_json(self, {"success": True})

        # ── Upload and parse resume ──
        elif self.path == '/api/upload_resume':
            import base64
            from generator.resume_parser import parse_pdf, parse_docx, extract_profile_with_ai

            body = json.loads(self._read_body().decode('utf-8'))
            filename = body.get('filename', '')
            b64_data = body.get('base64', '')
            file_bytes = base64.b64decode(b64_data.split(',')[1] if ',' in b64_data else b64_data)

            if filename.lower().endswith('.pdf'):
                text = parse_pdf(file_bytes)
            elif filename.lower().endswith('.docx'):
                text = parse_docx(file_bytes)
            else:
                text = file_bytes.decode('utf-8', errors='ignore')

            profile_data = extract_profile_with_ai(text)
            _send_json(self, {"success": True, "profile": profile_data})

        # ── Save config (API key, etc.) ──
        elif self.path == '/api/config':
            body = json.loads(self._read_body().decode('utf-8'))
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            config = {}
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as cf:
                    try:
                        config = json.load(cf)
                    except Exception:
                        pass
            config.update(body)
            with open(config_path, 'w', encoding='utf-8') as cf:
                json.dump(config, cf, indent=2)
            _send_json(self, {"success": True})

        # ── Save profiles ──
        elif self.path == '/api/profiles':
            profiles = json.loads(self._read_body().decode('utf-8'))
            profiles_path = os.path.join(os.path.dirname(__file__), 'generator', 'profiles.json')
            with open(profiles_path, 'w', encoding='utf-8') as pf:
                json.dump(profiles, pf, ensure_ascii=False, indent=2)
            _send_json(self, {"success": True})

        # ── Run harvest ──
        elif self.path == '/api/harvest':
            import subprocess
            script_path = os.path.join(os.path.dirname(__file__), 'harvest.py')
            result = subprocess.run(
                [sys.executable, script_path],   # use same python/venv
                capture_output=True, text=True, timeout=120
            )
            logs = result.stdout + ("\n" + result.stderr if result.stderr else "")
            _send_json(self, {"status": "done", "logs": logs.strip()})

        else:
            self.send_response(404)
            self.end_headers()


# ─────────────────────────────────────────────
#  Server startup
# ─────────────────────────────────────────────

import socket
from socketserver import ThreadingMixIn

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except Exception:
            pass
        super().server_bind()

def find_free_port(preferred_port=8115):
    for p in [preferred_port, 8115, 8116, 8117, 8118, 8120, 8125]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', p)) != 0:
                return p
    return preferred_port

def run_crm(port=None):
    if port is None:
        port = find_free_port(8115)
    server_address = ('', port)
    httpd = ThreadedHTTPServer(server_address, CRMHandler)
    with open(os.path.join(os.path.dirname(__file__), '.current_port'), 'w') as f:
        f.write(str(port))
    print(f"🚀 CRM запущен: http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == '__main__':
    run_crm()
