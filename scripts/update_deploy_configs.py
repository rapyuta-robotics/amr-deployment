#!/usr/bin/env python

import os
import shutil


package_names = {}
for (dirpath, dirnames, filenames) in os.walk("packages"):
    if filenames == []:
        continue
    latest_version = max(filenames).replace(".json", "")
    package_name = dirpath.replace("packages/", "") + "_version"
    package_names[package_name] = latest_version

with open("deploy_configs.yaml") as f:
    with open("deploy_configs_new.yaml", "w") as f2:
        for line in f:
            l = str(line)
            for package_name in package_names:
                if package_name in l:
                    l = package_name + ": \"" + package_names[package_name] + "\"\n"
                    break
            f2.writelines(l)


shutil.move("deploy_configs_new.yaml", "deploy_configs.yaml")
