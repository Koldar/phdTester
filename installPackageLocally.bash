PROJECT_LOCATION=$1
PIP="pip3"


function installIn {
	local pythonProject=$1
	local wheelFile=$2
	local venvLocation=$3
	source ${pythonProject}/${venvLocation}/bin/activate
	sudo ${PIP} install ${wheelFile}
	deactivate
}

function uninstall {
	local pythonPackage=$1
	if test `${PIP} freeze | grep ${pythonPackage} | wc -l` -gt 0
	then
		echo "Uninstall ${pythonPackage}..."
		sudo ${PIP} uninstall --yes ${pythonPackage}
	fi
}

# Create dist file
# @param 1 path of the python project location
# @param 2 location, relative to param 1, to the venv folder of the project (e.g., venv). No "/" at the end required
function createDist {
	local pythonProjectLocation=$1
	local venvLocation=$2

	oldPwd=`pwd`
	cd ${pythonProjectLocation}
	echo "we are in ${pythonProjectLocation}. Sourcing ${venvLocation}/bin/activate"
	source ${venvLocation}/bin/activate

	echo "Installing setuptools in venv"
	${PIP} install setuptools
	echo "Installing wheel in venv"
	${PIP} install wheel
	echo "Installing twine in venv"
	${PIP} install twine
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

# create wheel file
createDist ${PROJECT_LOCATION} venv

#uninstall package phdTester, if present
uninstall "phd-tester"

# install the package
whlFile=dist/$(ls --reverse dist/ | grep whl | head -n 1)

echo "Install ${whlFile}..."
sudo ${PIP} install ${whlFile}
echo "DONE!!!!"
