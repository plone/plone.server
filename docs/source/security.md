# Security

Security information for every operation is checked against three informations:

* Code definitions
* Local definitions
* Global definitions

Order or priority :

+ Local
+ Global
+ Code

Locally can be defined :

* A user/group has a permission in this object and its not inherit
* A user/group has a permission in this object and its going to be inherit
* A user/group has a forbitten permission in this object and its inherit

* A user/group has a role in this object and its not inherit
* A user/group has a role in this object and its inherit
* A user/group has a forbitten role in this object and its inherit

* A role has a permission in this object and its not inherit
* A role has a permission in this object and its inherit
* A role has a forbitten permission in this object and its inherit


Globally :

* This user/group has this Role
* This user/group has this Permission

Code :

* This user/group has this Role
* This user/group has this permission
* This role has this permission

