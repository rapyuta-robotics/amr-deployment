#!/usr/bin/env python

import os
import shutil

for (dirpath, dirnames, filenames) in os.walk("packages"):
    if filenames == []:
        continue
    latest_version = max(filenames).replace(".json", "")
    package_name = dirpath.replace("packages/", "") + "_version"

    with open("deploy_configs.yaml") as f:
        with open("deploy_configs_new.yaml", "w") as f2:
            for line in f:
                if package_name in line:
                    line = package_name + ": \"" + latest_version + "\"\n"
                f2.write(line)

shutil.move("deploy_configs_new.yaml", "deploy_configs.yaml")
