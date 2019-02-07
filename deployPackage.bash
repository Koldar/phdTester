USERNAME=$1
PASSWORD=$2
RELEASE=$3

source venv/bin/activate

pip install --user --upgrade setuptools wheel
pip install --user --upgrade twine
rm -rv dist/
python setup.py sdist bdist_wheel
twine check dist/*
twine upload --verbose --username ${USERNAME} --password=${PASSWORD} --repository-url https://test.pypi.org/legacy/ dist/*

if test $RELEASE = "true"
then
	#twine upload --verbose --username ${USERNAME} --password=${PASSWORD} --repository-url https://pypi.org/legacy/ dist/*
fi