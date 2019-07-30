from datetime import datetime
import json

j = json.dumps({'d': datetime.now().isoformat(), 'a': 'a'})
print(j)