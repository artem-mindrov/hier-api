# Usage

Requires Python 2.7 (the script was created and tested on 2.7.15) to be present in PATH:
```
C:\Users\bleak\PycharmProjects\hierarchy-api>set PATH=c:\Python27;%PATH

C:\Users\bleak\PycharmProjects\hierarchy-api>test_client_win.exe python hapi_server.py
Running test "add node nonexistent parent"
request : {"add_node":{"name":"tortulous-bilipurpurin","id":"1","parent_id":"0"}}

Test "add node nonexistent parent" passed
Running test "add root node"
request : {"add_node":{"name":"raiiform-italicize","id":"1","parent_id":""}}
...

Test "query names and ids" passed
Running test "add node no ID"
request : {"add_node":{"name":"epiploic-ruffianlike","id":"","parent_id":"1"}}

Test "add node no ID" passed

C:\Users\bleak\PycharmProjects\hierarchy-api>
```
