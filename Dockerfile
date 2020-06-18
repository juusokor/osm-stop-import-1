FROM python:3.9.0b3-alpine

ENV WORK /osm-stop-import
RUN mkdir -p ${WORK}
WORKDIR ${WORK}
COPY update-tags.py ${WORK}

CMD python update-tags.py -s ${INPUT} ${STOPS} ${OUTPUT}
