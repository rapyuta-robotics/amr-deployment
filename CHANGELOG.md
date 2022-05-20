# Changelog for rr_io_ansible repository

## 1.0.0 ##
------------------------
* Add CHANGELOG
* Added ability to insert component variables through config file
* DB can persist using db_persist: true
* Fixed package versions, they now show on rapyuta.io
* Package versions with form x.y.z-a can be used from rapyuta.io to deploy (requires requires rapyutarobotics-rr_io-2.1.0 from ansible galaxy)
* Volumes can be deployed (requires rapyutarobotics-rr_io-2.1.0 from ansible galaxy)
* Static routes for gwm and amr_ui for cloud deploy and simulation deploy

## 2.0.0 ##
------------------------
* Get only the newest version of a manifest. EG: `v22.03.1-2` and `v22.03.1.1`
    * The package created will be called v22.03.1 and in the description it will say it got it from v22.03.1-2.
    * It will ignore v22.03.1-1 because it is now old and there is a newer version