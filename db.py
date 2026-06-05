import asyncpg
import asyncio

DB_URL = ""

pool = None

async def connect_db():
    global pool
    try:
        pool = await asyncpg.create_pool(dsn=DB_URL)
        print("[DB] Connected to PostgreSQL ✅")
    except Exception as e:
        print(f"[DB] Connection Error: {e}")

async def init_db():
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                guild_id BIGINT PRIMARY KEY,
                nickname_toggle INTEGER DEFAULT 0,
                nickname_format TEXT DEFAULT 'User_{username}'
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS automod (
                guild_id BIGINT PRIMARY KEY,
                anti_invite INTEGER DEFAULT 0,
                anti_link INTEGER DEFAULT 0,
                anti_spam INTEGER DEFAULT 0
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS pin_messages (
                guild_id BIGINT,
                channel_id BIGINT,
                message TEXT,
                message_id BIGINT,
                enabled INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, channel_id)
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS log_settings (
                guild_id BIGINT PRIMARY KEY,
                log_channel_id BIGINT,
                log_enabled INTEGER DEFAULT 0
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS chatbot_settings (
                guild_id BIGINT PRIMARY KEY,
                channel_id BIGINT
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS regular_role (
                guild_id BIGINT PRIMARY KEY,
                role_id BIGINT,
                enabled INTEGER DEFAULT 0
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS count_channels (
                guild_id BIGINT PRIMARY KEY,
                channel_id BIGINT
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS count_progress (
                guild_id BIGINT PRIMARY KEY,
                count INTEGER DEFAULT 0,
                last_user_id BIGINT
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS dm_greet_settings (
                guild_id BIGINT PRIMARY KEY,
                enabled INTEGER DEFAULT 0,
                title TEXT DEFAULT 'Welcome {user}!',
                description TEXT DEFAULT 'Glad to have you in {server}!',
                image_url TEXT,
                footer TEXT
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS welcome_settings (
                guild_id BIGINT PRIMARY KEY,
                channel_id BIGINT,
                description TEXT DEFAULT 'Welcome {user} to {server}!',
                image_url TEXT,
                big_text TEXT DEFAULT 'Welcome!',
                small_text TEXT DEFAULT 'Enjoy your stay!',
                enabled INTEGER DEFAULT 0
            );
        ''')
        await conn.execute('''
             CREATE TABLE IF NOT EXISTS image_settings (
                guild_id BIGINT PRIMARY KEY,
                channel_id BIGINT,
                category TEXT
            );
        ''')

# -------------------- Nickname Settings --------------------

async def get_nick_setting(guild_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT nickname_toggle, nickname_format FROM settings WHERE guild_id = $1',
                guild_id
            )
            return (row['nickname_toggle'], row['nickname_format']) if row else (0, "User_{username}")
    except Exception as e:
        print(f"[DB] get_nick_setting error: {e}")
        return (0, "User_{username}")

async def set_nick_setting(guild_id, value):
    try:
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO settings (guild_id, nickname_toggle)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET nickname_toggle = EXCLUDED.nickname_toggle
            ''', guild_id, value)
    except Exception as e:
        print(f"[DB] set_nick_setting error: {e}")

async def set_nick_format(guild_id, format_str):
    try:
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO settings (guild_id, nickname_format)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET nickname_format = EXCLUDED.nickname_format
            ''', guild_id, format_str)
    except Exception as e:
        print(f"[DB] set_nick_format error: {e}")

# -------------------- Pin Messages --------------------

async def set_pin_message(guild_id, channel_id, message, message_id, enabled=True):
    try:
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO pin_messages (guild_id, channel_id, message, message_id, enabled)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (guild_id, channel_id) DO UPDATE
                SET message = EXCLUDED.message,
                    message_id = EXCLUDED.message_id,
                    enabled = EXCLUDED.enabled
            ''', guild_id, channel_id, message, message_id, int(enabled))
    except Exception as e:
        print(f"[DB] set_pin_message error: {e}")

async def get_pin_message(guild_id, channel_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT message, message_id FROM pin_messages WHERE guild_id = $1 AND channel_id = $2',
                guild_id, channel_id
            )
            return (row['message'], row['message_id']) if row else (None, None)
    except Exception as e:
        print(f"[DB] get_pin_message error: {e}")
        return (None, None)

async def set_pin_enabled(guild_id, channel_id, enabled):
    try:
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO pin_messages (guild_id, channel_id, enabled)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, channel_id) DO UPDATE
                SET enabled = EXCLUDED.enabled
            ''', guild_id, channel_id, int(enabled))
    except Exception as e:
        print(f"[DB] set_pin_enabled error: {e}")

async def is_pin_enabled(guild_id, channel_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT enabled FROM pin_messages WHERE guild_id = $1 AND channel_id = $2',
                guild_id, channel_id
            )
            return row['enabled'] == 1 if row else False
    except Exception as e:
        print(f"[DB] is_pin_enabled error: {e}")
        return False

async def get_full_pin_data(guild_id, channel_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT message, message_id, enabled FROM pin_messages WHERE guild_id = $1 AND channel_id = $2',
                guild_id, channel_id
            )
            return (row['message'], row['message_id'], row['enabled'] == 1) if row else (None, None, False)
    except Exception as e:
        print(f"[DB] get_full_pin_data error: {e}")
        return (None, None, False)

# -------------------- Logging --------------------

async def set_log_settings(guild_id, channel_id=None, enabled=None):
    try:
        async with pool.acquire() as conn:
            if channel_id is not None:
                await conn.execute('''
                    INSERT INTO log_settings (guild_id, log_channel_id)
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) DO UPDATE
                    SET log_channel_id = EXCLUDED.log_channel_id
                ''', guild_id, channel_id)
            if enabled is not None:
                await conn.execute('''
                    INSERT INTO log_settings (guild_id, log_enabled)
                    VALUES ($1, $2)
                    ON CONFLICT (guild_id) DO UPDATE
                    SET log_enabled = EXCLUDED.log_enabled
                ''', guild_id, int(enabled))
    except Exception as e:
        print(f"[DB] set_log_settings error: {e}")

async def get_log_channel_id(guild_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT log_channel_id FROM log_settings WHERE guild_id = $1',
                guild_id
            )
            return row['log_channel_id'] if row else None
    except Exception as e:
        print(f"[DB] get_log_channel_id error: {e}")
        return None

async def is_log_enabled(guild_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT log_enabled FROM log_settings WHERE guild_id = $1',
                guild_id
            )
            return row['log_enabled'] == 1 if row else False
    except Exception as e:
        print(f"[DB] is_log_enabled error: {e}")
        return False

# -------------------- Chatbot --------------------

async def set_chatbot_channel(guild_id, channel_id):
    try:
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO chatbot_settings (guild_id, channel_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET channel_id = EXCLUDED.channel_id
            ''', guild_id, channel_id)
    except Exception as e:
        print(f"[DB] set_chatbot_channel error: {e}")

async def get_chatbot_channel(guild_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT channel_id FROM chatbot_settings WHERE guild_id = $1',
                guild_id
            )
            return row['channel_id'] if row else None
    except Exception as e:
        print(f"[DB] get_chatbot_channel error: {e}")
        return None

async def remove_chatbot_channel(guild_id):
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                'DELETE FROM chatbot_settings WHERE guild_id = $1',
                guild_id
            )
    except Exception as e:
        print(f"[DB] remove_chatbot_channel error: {e}")

# -------------------- Regular Role --------------------

async def set_regular_role(guild_id, role_id):
    try:
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO regular_role (guild_id, role_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET role_id = EXCLUDED.role_id
            ''', guild_id, role_id)
    except Exception as e:
        print(f"[DB] set_regular_role error: {e}")

async def toggle_regular_role(guild_id, enabled):
    try:
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO regular_role (guild_id, enabled)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET enabled = EXCLUDED.enabled
            ''', guild_id, int(enabled))
    except Exception as e:
        print(f"[DB] toggle_regular_role error: {e}")

async def get_regular_role_settings(guild_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT role_id, enabled FROM regular_role WHERE guild_id = $1',
                guild_id
            )
            return (row['role_id'], row['enabled']) if row else (None, 0)
    except Exception as e:
        print(f"[DB] get_regular_role_settings error: {e}")
        return (None, 0)

# -------------------- Counting -----------------

async def set_count_channel(guild_id: int, channel_id: int):
    try:
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO count_channels (guild_id, channel_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET channel_id = EXCLUDED.channel_id
            ''', guild_id, channel_id)
    except Exception as e:
        print(f"[DB] set_count_channel error: {e}")

async def get_count_channel(guild_id: int):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT channel_id FROM count_channels WHERE guild_id = $1',
                guild_id
            )
            return row['channel_id'] if row else None
    except Exception as e:
        print(f"[DB] get_count_channel error: {e}")
        return None

async def remove_count_channel(guild_id: int):
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                'DELETE FROM count_channels WHERE guild_id = $1',
                guild_id
            )
    except Exception as e:
        print(f"[DB] remove_count_channel error: {e}")

async def get_current_count(guild_id: int):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT count FROM count_progress WHERE guild_id = $1',
                guild_id
            )
            return row['count'] if row else 0
    except Exception as e:
        print(f"[DB] get_current_count error: {e}")
        return 0

async def get_last_counter(guild_id: int):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT last_user_id FROM count_progress WHERE guild_id = $1',
                guild_id
            )
            return row['last_user_id'] if row else None
    except Exception as e:
        print(f"[DB] get_last_counter error: {e}")
        return None

async def update_count(guild_id: int, new_count: int, user_id: int):
    try:
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO count_progress (guild_id, count, last_user_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id) DO UPDATE
                SET count = EXCLUDED.count, last_user_id = EXCLUDED.last_user_id
            ''', guild_id, new_count, user_id)
    except Exception as e:
        print(f"[DB] update_count error: {e}")

async def reset_count(guild_id: int):
    try:
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO count_progress (guild_id, count, last_user_id)
                VALUES ($1, 0, NULL)
                ON CONFLICT (guild_id) DO UPDATE
                SET count = 0, last_user_id = NULL
            ''', guild_id)
    except Exception as e:
        print(f"[DB] reset_count error: {e}")

        # ----- image loop -----
async def set_image_setting(self, guild_id: int, channel_id: int, category: str):
    await self.pool.execute('''
        INSERT INTO image_settings (guild_id, channel_id, category)
        VALUES ($1, $2, $3)
        ON CONFLICT (guild_id) DO UPDATE
        SET channel_id = EXCLUDED.channel_id,
            category = EXCLUDED.category;
    ''', guild_id, channel_id, category)

async def get_image_setting(self, guild_id: int):
    row = await self.pool.fetchrow('''
        SELECT channel_id, category FROM image_settings
        WHERE guild_id = $1
    ''', guild_id)
    return dict(row) if row else None

async def clear_image_setting(self, guild_id: int):
    await self.pool.execute('''
        DELETE FROM image_settings WHERE guild_id = $1
    ''', guild_id)

async def get_all_image_settings(self):
    rows = await self.pool.fetch('''
        SELECT guild_id, channel_id, category FROM image_settings
    ''')
    return [dict(row) for row in rows]

# -------------------- DM Greet Settings --------------------

async def get_dm_greet_settings(guild_id):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT enabled, title, description, image_url, footer
                FROM dm_greet_settings
                WHERE guild_id = $1
            ''', guild_id)

            if row:
                return {
                    'enabled': bool(row['enabled']),
                    'title': row['title'],
                    'description': row['description'],
                    'image_url': row['image_url'],
                    'footer': row['footer']
                }

            return {
                'enabled': False,
                'title': 'Welcome {user}!',
                'description': 'Glad to have you in {server}!',
                'image_url': None,
                'footer': None
            }

    except Exception as e:
        print(f"[DB] get_dm_greet_settings error: {e}")
        return None


async def set_dm_greet_settings(guild_id, enabled=None, title=None, description=None, image_url=None, footer=None):
    try:
        async with pool.acquire() as conn:
            # Ensure row exists
            await conn.execute('''
                INSERT INTO dm_greet_settings (guild_id)
                VALUES ($1)
                ON CONFLICT (guild_id) DO NOTHING
            ''', guild_id)

            if enabled is not None:
                await conn.execute('''
                    UPDATE dm_greet_settings SET enabled = $1 WHERE guild_id = $2
                ''', int(enabled), guild_id)

            if title is not None:
                await conn.execute('''
                    UPDATE dm_greet_settings SET title = $1 WHERE guild_id = $2
                ''', title, guild_id)

            if description is not None:
                await conn.execute('''
                    UPDATE dm_greet_settings SET description = $1 WHERE guild_id = $2
                ''', description, guild_id)

            if image_url is not None:
                await conn.execute('''
                    UPDATE dm_greet_settings SET image_url = $1 WHERE guild_id = $2
                ''', image_url, guild_id)

            if footer is not None:
                await conn.execute('''
                    UPDATE dm_greet_settings SET footer = $1 WHERE guild_id = $2
                ''', footer, guild_id)

    except Exception as e:
        print(f"[DB] set_dm_greet_settings error: {e}")

        # -------------------- Image Settings --------------------

# Set or update the image posting settings for a guild
async def set_image_setting(guild_id: int, channel_id: int, category: str):
    try:
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO image_settings (guild_id, channel_id, category)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id)
                DO UPDATE SET 
                    channel_id = EXCLUDED.channel_id,
                    category = EXCLUDED.category
            ''', guild_id, channel_id, category)
    except Exception as e:
        print(f"[DB] set_image_setting error: {e}")

# Get the image posting settings for a specific guild
async def get_image_setting(guild_id: int):
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT channel_id, category 
                FROM image_settings
                WHERE guild_id = $1
            ''', guild_id)
            return {"channel_id": row["channel_id"], "category": row["category"]} if row else None
    except Exception as e:
        print(f"[DB] get_image_setting error: {e}")
        return None

# Get settings for all guilds (useful for background loops)
async def get_all_image_settings():
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch('SELECT guild_id, channel_id, category FROM image_settings')
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"[DB] get_all_image_settings error: {e}")
        return []

# Clear the image posting settings for a guild
async def clear_image_setting(guild_id: int):
    try:
        async with pool.acquire() as conn:
            await conn.execute('DELETE FROM image_settings WHERE guild_id = $1', guild_id)
    except Exception as e:
        print(f"[DB] clear_image_setting error: {e}")
