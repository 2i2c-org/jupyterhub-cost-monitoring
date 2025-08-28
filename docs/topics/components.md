# Components

This outlines the different components considered for cost calculations. We consider AWS services that are typically used in a Zero to JupyterHub deployment.

## Compute

We map AWS services to the compute component as follows:

- *Amazon Elastic Compute Cloud - Compute*
- *EC2 - Other*

Note that the *EC2 - Other* category includes costs associated with EBS volumes attached to EC2 instances, as well as costs associated with compute for core support nodes.

We therefore subtract the costs for home storage and support from the total compute costs to reflect only the costs associated with compute from user nodes.

## Home storage

We map AWS services to the home storage component as follows:

- *AWS Backup*
- *EC2 - Other*

We determine costs for the EBS volumes used for home directories from the **EC2 - Other** service by filtering on the tag `2i2c:volume-purpose=home-nfs`.

## Support

We map AWS services to the support component as follows:

- *Amazon Elastic Container Service for Kubernetes*
- *EC2 - Other*

We determine costs for the following:

- root EBS volumes attached to support core nodes by filtering on the tag `2i2c:node-purpose=core`
- hub databases by filtering on the tag `kubernetes.io/created-for/pvc/name= hub-db-dir`
- compute and storage for the Prometheus server, Grafana server and alertmanager by filtering on the tag `kubernetes.io/created-for/pvc/namespace= support`

## Object storage

TBC

## Networking

TBC