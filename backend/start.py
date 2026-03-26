import os
import sys

sys.path.append(os.path.dirname(__file__))

DB_PATH = os.path.join(os.path.dirname(__file__), "lucio.db")

if not os.path.exists(DB_PATH):
    print("Database not found - initializing...")
    from db import init_db
    init_db()
    from seed import main
    main()
    print("Database ready.")
else:
    print("Database exists - skipping seed.")

import uvicorn
port = int(os.environ.get("PORT", 8000))
uvicorn.run("api:app", host="0.0.0.0", port=port)
