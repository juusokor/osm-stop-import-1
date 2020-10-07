FROM python:3.8-slim
ENV WORK /osm-stop-import
RUN mkdir -p ${WORK}
WORKDIR ${WORK}
COPY update-tags.py ${WORK}
COPY requirements.txt ${WORK}
RUN pip install -r requirements.txt

ENTRYPOINT ["python", "update-tags.py"]
