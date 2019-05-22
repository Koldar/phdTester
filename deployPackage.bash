USERNAME=$1
PASSWORD=$2
RELEASE=$3


function installIn {
	local pythonProject=$1
	local wheelFile=$2
	source ${pythonProject}/venv/bin/activate
	pip install ${wheelFile}
	deactivate
}

function createDist {
	local pythonProject=$1

	oldPwd=`pwd`
	cd ${pythonProject}
	source venv/bin/activate

	pip install setuptools
	pip install wheel
	pip install twine
	rm -rfv dist/
	echo "python version is"
	python --version
	python setup.py sdist bdist_wheel
	twine check dist/*

	deactivate	
	cd ${oldPwd}
}

#pip install --user --upgrade setuptools wheel
#pip install --user --upgrade twine

createDist PhdTester
whlFile=$(ls PhdTester/dist/ | grep whl | head -n 1)
echo "wheel file to install is ${whlFile}"
installIn PhdTesterExample PhdTester/dist/${whlFile}

twine upload --verbose --username ${USERNAME} --password=${PASSWORD} --repository-url https://test.pypi.org/legacy/ dist/*

if test $RELEASE = "true"
then
	echo "uploading the projhect on pypi..."
	#twine upload --verbose --username ${USERNAME} --password=${PASSWORD} --repository-url https://pypi.org/legacy/ dist/*
fi

cd ..

echo "DONE!!!!"
echo "Checkout test project @"
