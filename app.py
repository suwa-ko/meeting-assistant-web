from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from flask_cors import CORS
import sqlite3
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import re
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

load_dotenv()
app = Flask(__name__)
# 生成一个随机密钥用于JWT签名
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', os.urandom(24).hex())
jwt = JWTManager(app)
CORS(app)

def get_db_connection():
    conn = sqlite3.connect('meeting_room.db', timeout=10.0)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    return conn


# 全局配置，允许运行时动态修改
global_settings = {
    "LMSTUDIO_API_URL": os.getenv("LMSTUDIO_API_URL", "http://localhost:3000/v1/chat/completions"),
    "LMSTUDIO_MODEL": os.getenv("LMSTUDIO_MODEL", "qwen/qwen3-4b-2507")
}

# ===================== 终极过滤：直接砍掉所有思考，只留最终中文答案 =====================
def ultra_clean(text):
    # 0. 删掉 <think>...</think> 标签及其内容 (兼容未闭合的 <think> 标签)
    text = re.sub(r'<think>[\s\S]*?(</think>|$)', '', text, flags=re.I)

    # 清理 Thinking Process 为开头的多余文本
    text = re.sub(r'Thinking Process[\s\S]*', '', text, flags=re.I)

    # 获取出 JSON 格式以防它被过滤破坏
    json_match = re.search(r'(\{.*?\})', text, flags=re.S)
    if json_match:
        # 如果包含JSON块，不进行普通话或者行过滤，直接返回当前文本（截取即可）
        return text.strip()

    # 如果纯对话，清空多余空行
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    clean_lines = [l for l in lines if any('\u4e00' <= c <= '\u9fff' for c in l)]

    if not clean_lines:
        return text.strip()

    return '\n'.join(clean_lines)

# 初始化数据库
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS meeting_rooms
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, capacity INTEGER, equipment TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reservations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, user_name TEXT,
                  start_time DATETIME, end_time DATETIME, meeting_topic TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')

    # 注入一个默认默认管理员账号，防止空表
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        hashed_pw = generate_password_hash("123456")
        c.execute("INSERT INTO users (username, password) VALUES (?,?)", ("admin", hashed_pw))

    if c.execute("SELECT COUNT(*) FROM meeting_rooms").fetchone()[0] == 0:
        c.executemany("INSERT INTO meeting_rooms (name,capacity,equipment) VALUES (?,?,?)",
            [("会议室A",10,"投影、白板"),("会议室B",20,"视频会议"),("会议室C",5,"投屏")])
    conn.commit()
    conn.close()

def call_qwen_stream(prompt, db_info="", custom_system_prompt=None, history=None, username="系统访客"):
    now = datetime.now()
    if custom_system_prompt:
        system_prompt = custom_system_prompt
    else:
        system_prompt = f"""当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')}，星期{now.isoweekday()}。你是专业的会议室管理助手。当前操作用户是：【{username}】。
请参考以下最新会议室及预约状态（作为你的判断依据）：
{db_info}

【核心交互原则】
- 日常沟通、查询、信息收集、冲突提示时，必须使用【纯中文自然语言】友好回复。
- 只有在【完全确认执行预约或取消动作】且信息完备、无冲突时，才输出【且仅输出纯 JSON】，不带任何多余文字和代码块标记。

【工作流与规则规范】
1. 状态查询：
   当用户询问占用情况或安排时，用自然语言并结合提供的状态数据回答。若有多条记录，使用列表（1. 2. 3.）和换行进行美观排版，绝对不要输出 JSON。
2. 预约会议：
   - 信息检查：首先核对关键要素（具体时间、要求/意向会议室、预约人、主题），若不全，请主动且友好地用自然语言向用户提问补全，绝不擅自捏造。（你可以优先把当前操作用户【{username}】作为默认预约人）。
   - 冲突检测：根据状态表核对是否有时间重叠、或设备不满足。若不满足，请用自然语言礼貌告知原因并主动推荐合适的替代方案。
   - 跨天/连续逻辑：如遇跨天或多日连续，请确保沟通确认后，在最终 JSON 动作中拆分为以天为单位的多次预约 (`batch_reserve`)。
   - 动作执行：确认无误后输出纯 JSON：
     单次：{{"action":"reserve","room_name":"会议室A","start_time":"YYYY-MM-DD HH:MM","end_time":"YYYY-MM-DD HH:MM","user_name":"姓名","topic":"主题"}}
     批量：{{"action":"batch_reserve","reserves":[{{"room_name":...}},...]}}
3. 取消会议：
   - 检查取消信息是否明确，如果在状态表中没找到该记录，用自然语言告知用户未能找到。
   - 权限检查：除了 user_name 是当前操作用户本人（【{username}】）或者是 admin，否则必须礼貌地拒绝取消他人的预约。
   - 确认无误后输出纯 JSON：
     {{"action":"cancel","room_name":"会议室A 或 all(代表全部)","start_time":"YYYY-MM-DD HH:MM 或 YYYY-MM-DD","user_name":"姓名"}}
4. 严格禁令：
   - 一旦你决定输出 JSON 执行实质动作，那就只输出 JSON 字符串本身（不要带格式化标签和前后文字说明）。
   - 禁止在回复里打印数据库原始的 [{{"id": ...}}] 结构给用户看。"""

    messages = [{"role":"system","content":system_prompt}]
    if history:
        for msg in history:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role":"user","content":prompt})

    data = {
        "model": global_settings["LMSTUDIO_MODEL"],
        "messages": messages,
        "temperature": 0.01,
        "max_tokens": 8192,
        "stream": True # 开启流式
    }
    try:
        resp = requests.post(global_settings["LMSTUDIO_API_URL"], json=data, timeout=600, stream=True)

        full_text = ""
        is_thinking = False

        for line in resp.iter_lines():
            if not line: continue
            line_text = line.decode('utf-8')
            if line_text.startswith("data: "):
                data_str = line_text[6:]
                if data_str == "[DONE]": break

                try:
                    chunk_json = json.loads(data_str)
                    content = chunk_json["choices"][0].get("delta", {}).get("content", "")
                except json.JSONDecodeError:
                    continue

                if not content: continue
                full_text += content

                # 思考状态的简易状态机判断
                if "<think>" in full_text and "</think>" not in full_text:
                    if not is_thinking:
                        is_thinking = True
                        yield f"data: {json.dumps({'type': 'think', 'content': '💡 正在思考排期...\\n'})}\n\n"
                    continue

                if "</think>" in content or ("</think>" in full_text and is_thinking):
                    is_thinking = False
                    # 此时我们可以过滤掉前面所有的内容，但基于流式为了防止把JSON的符号漏给前端
                    # 我们暂时继续看是否是JSON

                if not is_thinking:
                    # 如果疑似正在撰写 JSON（首字符或者带有 '{' 并且带 'action'），则拦截不在屏幕上显示
                    if "{" in full_text and "action" in full_text.lower():
                        continue
                    # 清理前面的 think ，避免意外外泄
                    clean_chunk = re.sub(r'<think>[\s\S]*?</think>', '', content, flags=re.I)
                    if clean_chunk:
                        yield f"data: {json.dumps({'type': 'chunk', 'content': clean_chunk})}\n\n"

        print(f"========== 模型原始输出 ==========\n{full_text}\n==================================")
        # 流发送完毕后，统揽全局，看是否需要执行动作
        cleaned_final = ultra_clean(full_text)
        action = parse_action(cleaned_final)
        if action:
            r = {"success": 0, "msg": "未知的操作指令"}
            if action["action"] == "reserve":
                r = do_reserve(action)
            elif action["action"] == "batch_reserve":
                r = do_batch_reserve(action)
            elif action["action"] == "cancel":
                r = do_cancel(action)
            yield f"data: {json.dumps({'type': 'action', 'content': r['msg'] if r['success'] else '❌ '+r['msg'], 'refresh': 1})}\n\n"
        elif "{" in full_text and "action" in full_text.lower():
            # 大模型尝试了输出 JSON 指令，但格式损坏导致无法解析，此时因为被拦截屏幕上可能为空，强制发出一个提示
            yield f"data: {json.dumps({'type': 'chunk', 'content': '🥲 抱歉，我明白您的意思，但大模型在生成操作指令时格式出现了损坏。请您稍加修改一下说法重新试一次。'})}\n\n"

    except requests.exceptions.RequestException as e:
        print(f"调用模型报错 (连接异常/超时): {e}")
        yield f"data: {json.dumps({'type': 'chunk', 'content': '🥲 哎呀，大模型助手开小差了（连接 LM Studio 失败或超时），请检查 AI 服务是否正常运行，稍后再试。'})}\n\n"
    except Exception as e:
        print(f"调用模型报错 (未知异常): {e}")
        yield f"data: {json.dumps({'type': 'chunk', 'content': '🥲 系统处理您的请求时遇到了点小障碍（生成格式异常），请您换换描述重新试一次。'})}\n\n"

# 解析动作JSON
def parse_action(text):
    if not text:
        return None
    try:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end+1]
            j = json.loads(json_str)
            if isinstance(j, dict) and j.get("action") in ["reserve", "cancel", "batch_reserve"]:
                return j
    except Exception as e:
        print(f"解析JSON报错: {e}")
    return None

# 执行取消预约
def do_cancel(info):
    try:
        conn = get_db_connection()
        c = conn.cursor()

        room_name = info.get("room_name", "")
        st_raw = info.get("start_time", "")
        user_name = info.get("user_name", "")

        is_all_rooms = room_name.lower() in ["all", "所有", "所有会议室", ""]

        # 应对 YYYY-MM-DD 或 YYYY-MM-DD HH:MM
        date_prefix = st_raw[:10] if st_raw else ""
        st_formatted = ""
        if st_raw and len(st_raw) > 10:
            try:
                st_formatted = datetime.strptime(st_raw, "%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        if is_all_rooms:
            query = "DELETE FROM reservations WHERE 1=1"
            select_query = "SELECT COUNT(*) FROM reservations WHERE 1=1"
            params = []
            if date_prefix:
                query += " AND start_time LIKE ?"
                select_query += " AND start_time LIKE ?"
                params.append(date_prefix + "%")
            if user_name:
                query += " AND user_name = ?"
                select_query += " AND user_name = ?"
                params.append(user_name)

            c.execute(select_query, params)
            count = c.fetchone()[0]
            if count == 0:
                conn.close()
                return {"success": 0, "msg": "未找到匹配的预约记录，无法批量取消。"}

            c.execute(query, params)
            conn.commit()
            conn.close()
            return {"success": 1, "msg": f"✅批量取消成功！已为您撤销了 {count} 条预约记录。"}

        # 针对指定会议室的取消逻辑
        c.execute("SELECT id FROM meeting_rooms WHERE name=?", (room_name,))
        room = c.fetchone()
        if not room:
            conn.close()
            return {"success":0,"msg":"无此会议室"}
        rid = room[0]

        if st_formatted:
            c.execute("SELECT id FROM reservations WHERE room_id=? AND user_name=? AND start_time=?", (rid, user_name, st_formatted))
        else:
            c.execute("SELECT id FROM reservations WHERE room_id=? AND user_name=? AND start_time LIKE ?", (rid, user_name, date_prefix+"%"))

        res = c.fetchone()
        if not res and st_formatted:
            # 宽泛匹配日期
            c.execute("SELECT id FROM reservations WHERE room_id=? AND user_name=? AND start_time LIKE ?", (rid, user_name, date_prefix+"%"))
            res = c.fetchone()

        if not res:
            conn.close()
            return {"success":0, "msg":"未找到匹配的预约记录，请确认您的会议室、姓名和原定时间是否正确。"}

        c.execute("DELETE FROM reservations WHERE id=?", (res[0],))
        conn.commit()
        conn.close()
        return {"success":1,"msg":f"✅取消成功！已为您撤销：{room_name} 的相关预约。"}
    except Exception as e:
        return {"success":0,"msg":f"取消请求格式无法识别: {str(e)}"}

# 执行预约
def do_reserve(info):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM meeting_rooms WHERE name=?",(info["room_name"],))
        room = c.fetchone()
        if not room:return {"success":0,"msg":"无此会议室"}
        rid = room[0]
        st = datetime.strptime(info["start_time"],"%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M:%S")
        et = datetime.strptime(info["end_time"],"%Y-%m-%d %H:%M").strftime("%Y-%m-%d %H:%M:%S")
        # 修正冲突判断逻辑: 新时间段(st, et)与现有时间段(start_time, end_time)如果存在交集，即: 新开始时间 < 现有结束时间 且 新结束时间 > 现有开始时间
        c.execute("SELECT COUNT(*) FROM reservations WHERE room_id=? AND (? < end_time AND ? > start_time)",
                 (rid,st,et))
        if c.fetchone()[0]>0:return {"success":0,"msg":"时间段冲突"}
        c.execute("INSERT INTO reservations (room_id,user_name,start_time,end_time,meeting_topic) VALUES (?,?,?,?,?)",
                 (rid,info["user_name"],st,et,info["topic"]))
        conn.commit()
        conn.close()
        return {"success":1,"msg":f"✅预约成功！{info['room_name']} {info['start_time']} 至 {info['end_time']}"}
    except Exception as e:
        return {"success":0,"msg":f"预约格式错误: {str(e)}"}

# 执行批量预约
def do_batch_reserve(info):
    reserves = info.get("reserves", [])
    if not reserves:
        return {"success": 0, "msg": "未提取到有效的预约列表"}

    success_count = 0
    msgs = []
    for res in reserves:
        r = do_reserve(res)
        room_n = res.get('room_name', '未知会议室')
        st_t = res.get('start_time', '未知时间')
        if r["success"]:
            success_count += 1
            msgs.append(f"✅ {room_n} ({st_t}) 预约成功")
        else:
            msgs.append(f"❌ {room_n} ({st_t}): {r['msg']}")

    if success_count == len(reserves) and len(reserves) > 0:
        return {"success": 1, "msg": f"✅全部预约成功！共预约 {success_count} 条记录。\n" + "\n".join(msgs)}
    elif success_count > 0:
        return {"success": 1, "msg": f"⚠️部分预约成功（{success_count}/{len(reserves)}）。详情：\n" + "\n".join(msgs)}
    else:
        return {"success": 0, "msg": "❌预约全部失败：\n" + "\n".join(msgs)}

# 路由
@app.route('/')
def index():return render_template('index.html')

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/api/admin/rooms', methods=["GET", "POST", "PUT", "DELETE"])
@jwt_required()
def admin_rooms():
    current_user = get_jwt_identity()
    if current_user != "admin":
        return jsonify({"success": 0, "msg": "权限不足，仅限管理员账号访问此接口"})

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        if request.method == "GET":
            rooms = [dict(r) for r in c.execute("SELECT * FROM meeting_rooms").fetchall()]
            return jsonify({"success": 1, "rooms": rooms})

        elif request.method == "POST":
            data = request.json
            name = data.get("name", "").strip()
            if not name: return jsonify({"success": 0, "msg": "会议室名称不能为空"})
            c.execute("INSERT INTO meeting_rooms (name, capacity, equipment) VALUES (?,?,?)",
                      (name, data.get("capacity", 10), data.get("equipment", "")))
            conn.commit()
            return jsonify({"success": 1, "msg": "添加成功"})

        elif request.method == "PUT":
            data = request.json
            room_id = data.get("id")
            name = data.get("name", "").strip()
            if not name: return jsonify({"success": 0, "msg": "会议室名称不能为空"})
            c.execute("UPDATE meeting_rooms SET name=?, capacity=?, equipment=? WHERE id=?",
                      (name, data.get("capacity", 10), data.get("equipment", ""), room_id))
            conn.commit()
            return jsonify({"success": 1, "msg": "修改成功"})

        elif request.method == "DELETE":
            room_id = request.json.get("id")
            c.execute("DELETE FROM meeting_rooms WHERE id=?", (room_id,))
            c.execute("DELETE FROM reservations WHERE room_id=?", (room_id,))
            conn.commit()
            return jsonify({"success": 1, "msg": "删除成功"})
    except Exception as e:
        return jsonify({"success": 0, "msg": f"操作出错: {str(e)}"})
    finally:
        conn.close()

@app.route('/api/admin/reservations', methods=["GET", "POST", "DELETE"])
@jwt_required()
def admin_reservations():
    current_user = get_jwt_identity()
    if current_user != "admin":
        return jsonify({"success": 0, "msg": "权限不足，仅限管理员账号访问"})

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        if request.method == "GET":
            query = '''SELECT r.id, r.user_name, r.start_time, r.end_time, r.meeting_topic, m.name as room_name
                       FROM reservations r
                       LEFT JOIN meeting_rooms m ON r.room_id = m.id
                       ORDER BY r.start_time DESC'''
            reservations = [dict(row) for row in c.execute(query).fetchall()]
            return jsonify({"success": 1, "reservations": reservations})
        elif request.method == "POST":
            data = request.json
            room_id = data.get("room_id")
            user_name = data.get("user_name", "").strip()
            start_time = data.get("start_time", "").strip()
            end_time = data.get("end_time", "").strip()
            topic = data.get("meeting_topic", "管理后台批量新增").strip()

            if not all([room_id, user_name, start_time, end_time]):
                return jsonify({"success": 0, "msg": "包含必填项为空"})

            try:
                st = start_time.replace("T", " ")
                if len(st) == 16: st += ":00"
                et = end_time.replace("T", " ")
                if len(et) == 16: et += ":00"

                c.execute("SELECT COUNT(*) FROM reservations WHERE room_id=? AND (? < end_time AND ? > start_time)", (room_id, st, et))
                if c.fetchone()[0] > 0:
                    return jsonify({"success": 0, "msg": "时间冲突，该时段已被占用！"})

                c.execute("INSERT INTO reservations (room_id, user_name, start_time, end_time, meeting_topic) VALUES (?,?,?,?,?)",
                          (room_id, user_name, st, et, topic))
                conn.commit()
                return jsonify({"success": 1, "msg": "新增预约成功"})
            except Exception as e:
                return jsonify({"success": 0, "msg": f"错误: {str(e)}"})
        elif request.method == "DELETE":
            res_ids = request.json.get("ids", [])
            if not isinstance(res_ids, list) or not res_ids:
                return jsonify({"success": 0, "msg": "请提供要删除的预约ID列表"})

            placeholders = ','.join('?' * len(res_ids))
            c.execute(f"DELETE FROM reservations WHERE id IN ({placeholders})", res_ids)
            conn.commit()
            return jsonify({"success": 1, "msg": f"成功删除了 {len(res_ids)} 条预约"})
    except Exception as e:
        return jsonify({"success": 0, "msg": f"操作出错: {str(e)}"})
    finally:
        conn.close()

@app.route('/api/room_status')
def room_status():
    d = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    conn = get_db_connection()
    conn.row_factory=sqlite3.Row
    c=conn.cursor()
    rooms = [dict(r) for r in c.execute("SELECT * FROM meeting_rooms").fetchall()]
    for r in rooms:
        r["reservations"] = [dict(x) for x in c.execute(
            "SELECT start_time,end_time,user_name,meeting_topic FROM reservations WHERE room_id=? AND DATE(start_time)=?",
            (r["id"],d)).fetchall()]
    conn.close()
    return jsonify(rooms)

@app.route('/api/settings', methods=["GET", "POST"])
def settings_api():
    if request.method == "POST":
        new_model = request.json.get("model")
        if new_model in ["qwen/qwen3-4b-2507", "qwen3.5-35b-a3b"]:
            global_settings["LMSTUDIO_MODEL"] = new_model
            return jsonify({"success": 1, "msg": "设置已保存"})
        return jsonify({"success": 0, "msg": "无效的模型选择"})
    return jsonify({
        "model": global_settings["LMSTUDIO_MODEL"]
    })

@app.route('/api/login', methods=["POST"])
def login():
    username = request.json.get("username", "").strip()
    password = request.json.get("password", "").strip()

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()

    if user:
        db_pwd = user[0]
        # 兼容老用户明文密码与新用户哈希密码
        if db_pwd.startswith('scrypt:') or db_pwd.startswith('pbkdf2:'):
            is_valid = check_password_hash(db_pwd, password)
        else:
            is_valid = (db_pwd == password)

        if is_valid:
            # 签发真实的 JWT 令牌，而不是伪造的字符串
            access_token = create_access_token(identity=username)
            return jsonify({"success": 1, "username": username, "token": access_token})

    return jsonify({"success": 0, "msg": "用户名或密码错误，请重试或先注册账号。"})

@app.route('/api/register', methods=["POST"])
def register():
    username = request.json.get("username", "").strip()
    password = request.json.get("password", "").strip()
    if not username or not password:
        return jsonify({"success": 0, "msg": "用户名或密码不能为空"})

    conn = get_db_connection()
    c = conn.cursor()
    try:
        # 对密码进行安全哈希加密
        hashed_pw = generate_password_hash(password)
        c.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, hashed_pw))
        conn.commit()
        success = True
        msg = "注册成功，请使用新账号登录！"
    except sqlite3.IntegrityError:
        success = False
        msg = "该用户名已被占用，请换一个。"
    finally:
        conn.close()

    if success:
        return jsonify({"success": 1, "msg": msg})
    else:
        return jsonify({"success": 0, "msg": msg})

@app.route('/api/ai_chat',methods=["POST"])
@jwt_required()
def ai_chat():
    username = get_jwt_identity() # 必须是从 Token 解析出来的身份，防止前端伪造
    p = request.json.get("prompt","").strip()
    history = request.json.get("history", [])
    username = request.json.get("username", "系统访客")
    if not p:return jsonify({"content":"请输入指令","refresh":0})

    # 获取数据库当前状态供AI参考
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    rooms = [dict(r) for r in c.execute("SELECT * FROM meeting_rooms").fetchall()]
    for r in rooms:
        r["reservations"] = [dict(x) for x in c.execute(
            "SELECT start_time,end_time,user_name,meeting_topic FROM reservations WHERE room_id=?",
            (r["id"],)).fetchall()]
    conn.close()

    db_info = json.dumps(rooms, ensure_ascii=False)

    return Response(stream_with_context(call_qwen_stream(p, db_info, history=history, username=username)), mimetype='text/event-stream')

@app.route('/api/meeting_summary',methods=["POST"])
@jwt_required()
def meeting_summary():
    text = request.json.get("text","").strip()
    if not text:
        return jsonify({"content": "获取不到录音内容"})

    system_prompt = """你是一个专业的会议助理。请根据用户提供的会议对话或记录，生成一份结构清晰、重点突出的会议纪要。包含：
1. 会议核心议题
2. 主要决定及共识
3. 后续待办事项及负责人（如有提及）
确保条理分明。"""

    # For meeting summary, we won't stream immediately for simplicity, but we can reuse the stream mechanism and collect it.
    ai_resp_generator = call_qwen_stream(text, db_info="", custom_system_prompt=system_prompt)

    full_resp = ""
    for data_str in ai_resp_generator:
        # Here we only grab 'chunk'
        try:
            if data_str.startswith("data: "):
                j = json.loads(data_str[6:])
                if j.get("type") == "chunk":
                    full_resp += j.get("content", "")
        except:
            pass

    return jsonify({"content": full_resp})

init_db()
if __name__ == '__main__':
    from waitress import serve
    print("🚀 生产级并发服务器(Waitress)已启动: http://0.0.0.0:5000")
    print("👉 本地访问请打开: http://127.0.0.1:5000")
    print("👉 局域网访问请使用您的电脑IP，例如: http://192.168.x.x:5000")
    serve(app, host="0.0.0.0", port=5000, threads=8)
