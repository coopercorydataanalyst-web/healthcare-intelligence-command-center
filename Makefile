.PHONY: data train test reproduce

data:
	python etl/fetch_cms.py

train:
	python ml/train_census_forecast.py
	python models/cms/train_cms_model.py

test:
	pytest -q

reproduce: data train test
