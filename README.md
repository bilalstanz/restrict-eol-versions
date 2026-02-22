# Restrict-eol-versions
Contains CI + TF module workflow for aws service that saves extended support fees by stopping infra creation of legacy/eol versions and forcing the hard decisions earlier

​    

### Purpose / Problem

Sometimes in wake of speed teams copy entire terraform infra that had previously worked,  while this brings much needed speed it also drives a silent cost if that old infra service versions went under legacy/eol,  this cost comes as extended support fees,  while teams can change version in TF file there is no rail-guard by aws to stop it and thus a solution was required to force a hard decision earlier on

​    

### Usage

Anyone can call this module from their terraform file and they would be forced to use only currently supported/standard versions,

​    

### what does it do

it stops legacy/eol version being spawned by terraform

​    

### How does it work

##### Currently this repo contains 3 components -

eks module with aws service version constraint,

python script which checks if any version has gone out of support then updates version number in module

CI pipeline that keeps running python script in schedule and checks if version file is updated then commits the new updated version,
You can check actions tab for info





