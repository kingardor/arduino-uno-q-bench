# YOLOE-26n detection sidecar (NCNN FP16, CPU). Built on the board (has internet
# on the default docker bridge). The ncnn model is bind-mounted at /models.
FROM python:3.11-slim
RUN pip install --no-cache-dir ncnn numpy pillow
COPY detect_server.py /detect_server.py
EXPOSE 7801
CMD ["python", "/detect_server.py"]
