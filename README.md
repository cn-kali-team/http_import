# httpimp
- 远程内存加载Python模块

```python
import sys
import http_import

sys.path.append('http://localhost:8000')
http_import.install_path_hook()
import requests
print(dir(requests))
```

- 开启http服务，`python3 -m http.server`

![demo](README.assets/demo.png)

