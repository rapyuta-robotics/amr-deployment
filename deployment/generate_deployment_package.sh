#script to create zip file which is shared with client
tmp_dir=$(mktemp -d)
current_dir=$(pwd)

cp -r packages requests $tmp_dir
cp requirements.txt deploy.py README.md $tmp_dir

#copy only necessary files
mkdir $tmp_dir/config
cp config/$1.yaml config/default*.yaml $tmp_dir/config

cd $tmp_dir
zip -r $current_dir/deployment.zip *

cd -
