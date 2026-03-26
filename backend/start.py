import os
import sys

sys.path.append(os.path.dirname(__file__))

DB_PATH = os.path.join(os.path.dirname(__file__), "lucio.db")

# Always reseed to pick up latest merchant data
print("Initializing database...")
from db import init_db
init_db()
from seed import main
main()
print("Database ready.")

import uvicorn
port = int(os.environ.get("PORT", 8000))
uvicorn.run("api:app", host="0.0.0.0", port=port)
