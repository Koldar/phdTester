PROJECT_LOCATION=$1


function installIn {
	local pythonProject=$1
	local wheelFile=$2
	local venvLocation=$3
	source ${pythonProject}/${venvLocation}/bin/activate
	sudo pip install ${wheelFile}
	deactivate
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
	pip install setuptools
	echo "Installing wheel in venv"
	pip install wheel
	echo "Installing twine in venv"
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

createDist ${PROJECT_LOCATION} venv
whlFile=$(ls ${PROJECT_LOCATION}/dist/ | grep whl | head -n 1)
echo "DONE!!!!"
