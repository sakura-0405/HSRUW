該程式有使用到 wmi 和 pywin32 ，
因此該程式僅為windows系統提供服務。

該軟體會讀取硬體資訊，所以大概率會被視為病毒，
但無須擔心，該exe檔為py檔所打包，且完全開源。
如有疑慮，可檢查py檔內的程式碼後，直接使用終端機執行，或是重新打包。

This program utilizes `wmi` and `pywin32`, meaning it is exclusively designed for Windows operating systems.

Since the software retrieves real-time hardware information, there is a high probability that it might be flagged as a false positive by antivirus software. 
However, there is no need for concern: the executable (`.exe`) is compiled directly from the Python script, and the entire project is completely open-source. 
If you have any security concerns, you are welcome to inspect the source code in the `.py` file and run it directly via the terminal or repackage it yourself.
