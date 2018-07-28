import unittest
from unittest.mock import Mock

from auto_peering.vpc_links import VPCLinks
from auto_peering.vpc_link import VPCLink


def tags_for(component, deployment_identifier, dependencies):
    return [
        {'Key': 'Component', 'Value': component},
        {'Key': 'DeploymentIdentifier', 'Value': deployment_identifier},
        {'Key': 'Dependencies', 'Value': ','.join(dependencies)}
    ]


class TestVPCLinks(unittest.TestCase):
    def test_resolve_dependencies_for_target_vpc(self):
        target_vpc_id = 'vpc-12345678'

        target_vpc = Mock(name='Target VPC')
        target_vpc.id = target_vpc_id
        target_vpc.tags = tags_for(
            'thing1', 'gold', ['thing2-silver', 'thing3-bronze'])

        dependency_vpc1 = Mock(name='Dependency VPC 1')
        dependency_vpc1.tags = tags_for('thing2', 'silver', [])
        dependency_vpc2 = Mock(name='Dependency VPC 2')
        dependency_vpc2.tags = tags_for('thing3', 'bronze', [])

        dependent_vpc = Mock(name='Dependent VPC')
        dependent_vpc.tags = tags_for('thing4', 'lead', ['thing1-gold'])

        other_vpc = Mock(name='Other VPC')
        other_vpc.tags = tags_for('other-thing', 'copper', [])

        region = 'eu-west-1'
        ec2_resource = Mock(name='EC2 resource')
        ec2_resources = {region: ec2_resource}
        logger = Mock(name='Logger')

        ec2_resource.vpcs.all = Mock(
            name='All VPCs',
            return_value=iter(
                [dependency_vpc1,
                 target_vpc,
                 dependent_vpc,
                 other_vpc,
                 dependency_vpc2]))

        vpc_links = VPCLinks(ec2_resources, logger)
        resolved_vpc_links = vpc_links.resolve_for(target_vpc_id)

        self.assertEqual(
            resolved_vpc_links,
            {VPCLink(target_vpc, dependency_vpc1,
                     ec2_resources, logger),
             VPCLink(target_vpc, dependency_vpc2,
                     ec2_resources, logger),
             VPCLink(dependent_vpc, target_vpc,
                     ec2_resources, logger)})

    def test_resolves_using_multiple_ec2_resources(self):
        target_vpc_id = 'vpc-12345678'

        target_vpc = Mock(name='Target VPC')
        target_vpc.id = target_vpc_id
        target_vpc.tags = tags_for(
            'thing1', 'gold', ['thing2-silver', 'thing3-bronze'])

        dependency_vpc1 = Mock(name='Dependency VPC 1')
        dependency_vpc1.tags = tags_for('thing2', 'silver', [])
        dependency_vpc2 = Mock(name='Dependency VPC 2')
        dependency_vpc2.tags = tags_for('thing3', 'bronze', [])

        dependent_vpc = Mock(name='Dependent VPC')
        dependent_vpc.tags = tags_for('thing4', 'lead', ['thing1-gold'])

        other_vpc = Mock(name='Other VPC')
        other_vpc.tags = tags_for('other-thing', 'copper', [])

        region_1 = 'eu-west-1'
        ec2_resource_1 = Mock(name='EC2 resource')
        region_2 = 'us-east-1'
        ec2_resource_2 = Mock(name='EC2 resource')

        ec2_resources = {
            region_1: ec2_resource_1,
            region_2: ec2_resource_2
        }

        logger = Mock(name='Logger')

        ec2_resource_1.vpcs.all = Mock(
            name='All VPCs in {}'.format(region_1),
            return_value=iter(
                [dependency_vpc1,
                 target_vpc,
                 dependent_vpc]))

        ec2_resource_2.vpcs.all = Mock(
            name='All VPCs in {}'.format(region_2),
            return_value=iter(
                [dependency_vpc2,
                 other_vpc]))

        vpc_links = VPCLinks(ec2_resources, logger)
        resolved_vpc_links = vpc_links.resolve_for(target_vpc_id)

        self.assertEqual(
            resolved_vpc_links,
            {VPCLink(target_vpc, dependency_vpc1,
                     ec2_resources, logger),
             VPCLink(target_vpc, dependency_vpc2,
                     ec2_resources, logger),
             VPCLink(dependent_vpc, target_vpc,
                     ec2_resources, logger)})

    def test_resolves_no_duplicates(self):
        vpc1_id = "vpc-12345678"

        vpc1 = Mock(name="VPC 1")
        vpc1.id = vpc1_id
        vpc1.tags = tags_for('thing1', 'gold', ['thing2-silver'])

        vpc2 = Mock(name="VPC 2")
        vpc2.tags = tags_for('thing2', 'silver', ['thing1-gold'])

        region = 'eu-west-1'
        ec2_resource = Mock(name="EC2 resource")
        ec2_resources = {region: ec2_resource}
        logger = Mock(name="Logger")

        ec2_resource.vpcs.all = Mock(
            name="All VPCs",
            return_value=iter(
                [vpc1,
                 vpc2]))

        vpc_links = VPCLinks(ec2_resources, logger)
        resolved_vpc_links = vpc_links. \
            resolve_for(vpc1_id)

        self.assertEqual(
            resolved_vpc_links,
            {VPCLink(vpc1, vpc2,
                     ec2_resources, logger)})

    def test_logs_found_target_vpc(self):
        vpc1_id = "vpc-12345678"

        vpc1 = Mock(name="VPC 1")
        vpc1.id = vpc1_id
        vpc1.tags = tags_for('thing1', 'gold', ['thing2-silver'])

        vpc2 = Mock(name="VPC 2")
        vpc2.tags = tags_for('thing2', 'silver', [])

        region = 'eu-west-1'
        ec2_resource = Mock(name="EC2 resource")
        ec2_resources = {region: ec2_resource}
        logger = Mock(name="Logger")

        ec2_resource.vpcs.all = Mock(
            name="All VPCs",
            return_value=iter(
                [vpc1,
                 vpc2]))

        vpc_links = VPCLinks(ec2_resources, logger)
        vpc_links.resolve_for(vpc1_id)

        logger.debug.assert_any_call(
            "Computing VPC links for VPC with ID: '%s'.", vpc1.id)
        logger.debug.assert_any_call(
            "Found target VPC with ID: '%s', component: '%s', "
            "deployment identifier: '%s' and dependencies: '%s'.",
            vpc1.id, 'thing1', 'gold', ['thing2-silver'])

    def test_logs_not_found_target_vpc(self):
        vpc1_id = "vpc-12345678"

        vpc1 = Mock(name="VPC 1")
        vpc1.id = vpc1_id
        vpc1.tags = tags_for('thing1', 'gold', ['thing2-silver'])

        region = 'eu-west-1'
        ec2_resource = Mock(name="EC2 resource")
        ec2_resources = {region: ec2_resource}
        logger = Mock(name="Logger")

        ec2_resource.vpcs.all = Mock(
            name="All VPCs",
            return_value=iter([]))

        vpc_links = VPCLinks(ec2_resources, logger)
        vpc_links.resolve_for(vpc1_id)

        logger.debug.assert_any_call(
            "No VPC found with ID: '%s'. Aborting.", vpc1.id)

    def test_resolves_empty_set_for_missing_target_vpc(self):
        vpc1_id = "vpc-12345678"

        vpc1 = Mock(name="VPC 1")
        vpc1.id = vpc1_id
        vpc1.tags = tags_for('thing1', 'gold', ['thing2-silver'])

        region = 'eu-west-1'
        ec2_resource = Mock(name="EC2 resource")
        ec2_resources = {region: ec2_resource}
        logger = Mock(name="Logger")

        ec2_resource.vpcs.all = Mock(
            name="All VPCs",
            return_value=iter([]))

        vpc_links = VPCLinks(ec2_resources, logger)
        resolved_vpc_links = vpc_links.resolve_for(vpc1_id)

        self.assertEqual(resolved_vpc_links, set())

    def test_ignores_missing_dependencies(self):
        vpc1_id = "vpc-12345678"

        vpc1 = Mock(name="VPC 1")
        vpc1.id = vpc1_id
        vpc1.tags = tags_for(
            'thing1', 'gold', ['thing2-silver', 'thing3-bronze'])

        vpc2 = Mock(name="VPC 2")
        vpc2.tags = tags_for('thing2', 'silver', [])

        region = 'eu-west-1'
        ec2_resource = Mock(name="EC2 resource")
        ec2_resources = {region: ec2_resource}
        logger = Mock(name="Logger")

        ec2_resource.vpcs.all = Mock(
            name="All VPCs",
            return_value=iter(
                [vpc1,
                 vpc2]))

        vpc_links = VPCLinks(ec2_resources, logger)
        resolved_vpc_links = vpc_links.resolve_for(vpc1_id)

        self.assertEqual(len(resolved_vpc_links), 1)
        self.assertEqual(
            resolved_vpc_links,
            {VPCLink(vpc1, vpc2, ec2_resources, logger)})

    def test_logs_dependency_vpcs(self):
        target_vpc_id = "vpc-12345678"

        target_vpc = Mock(name="Target VPC")
        target_vpc.id = target_vpc_id
        target_vpc.tags = tags_for(
            'thing1', 'gold', ['thing2-silver', 'thing3-bronze'])

        dependency_vpc1 = Mock(name="Dependency VPC 1")
        dependency_vpc1.id = "vpc-d1a1a1a1"
        dependency_vpc1.tags = tags_for('thing2', 'silver', [])

        dependency_vpc2 = Mock(name="Dependency VPC 2")
        dependency_vpc2.id = "vpc-d2a2a2a2"
        dependency_vpc2.tags = tags_for('thing3', 'bronze', [])

        region = 'eu-west-1'
        ec2_resource = Mock(name="EC2 resource")
        ec2_resources = {region: ec2_resource}
        logger = Mock(name="Logger")

        ec2_resource.vpcs.all = Mock(
            name="All VPCs",
            return_value=iter(
                [dependency_vpc1,
                 target_vpc,
                 dependency_vpc2]))

        vpc_links = VPCLinks(ec2_resources, logger)
        vpc_links.resolve_for(target_vpc_id)

        logger.debug.assert_any_call(
            "Found dependency VPCs: [%s]",
            "'thing2-silver':'vpc-d1a1a1a1', 'thing3-bronze':'vpc-d2a2a2a2'")

    def test_logs_dependent_vpcs(self):
        target_vpc_id = "vpc-12345678"

        target_vpc = Mock(name="Target VPC")
        target_vpc.id = target_vpc_id
        target_vpc.tags = tags_for('thing1', 'gold', [])

        dependent_vpc1 = Mock(name="Dependent VPC 1")
        dependent_vpc1.id = "vpc-d1a1a1a1"
        dependent_vpc1.tags = tags_for('thing2', 'silver', ['thing1-gold'])

        dependent_vpc2 = Mock(name="Dependent VPC 2")
        dependent_vpc2.id = "vpc-d2a2a2a2"
        dependent_vpc2.tags = tags_for('thing3', 'bronze', ['thing1-gold'])

        region = 'eu-west-1'
        ec2_resource = Mock(name="EC2 resource")
        ec2_resources = {region: ec2_resource}
        logger = Mock(name="Logger")

        ec2_resource.vpcs.all = Mock(
            name="All VPCs",
            return_value=iter(
                [dependent_vpc1,
                 target_vpc,
                 dependent_vpc2]))

        vpc_links = VPCLinks(ec2_resources, logger)
        vpc_links.resolve_for(target_vpc_id)

        logger.debug.assert_any_call(
            "Found dependent VPCs: [%s]",
            "'thing2-silver':'vpc-d1a1a1a1', 'thing3-bronze':'vpc-d2a2a2a2'")