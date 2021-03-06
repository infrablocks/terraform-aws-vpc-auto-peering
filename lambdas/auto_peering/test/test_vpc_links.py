import unittest
from unittest.mock import Mock

from auto_peering.vpc import VPC
from auto_peering.vpc_links import VPCLinks
from auto_peering.vpc_link import VPCLink

from test import randoms, builders, mocks


class TestVPCLinks(unittest.TestCase):
    def test_resolve_dependencies_for_target_vpc(self):
        account_id = randoms.account_id()
        region = randoms.region()
        target_vpc_id = randoms.vpc_id()

        target_vpc_response = mocks.build_vpc_response_mock(
            id=target_vpc_id,
            name="Target VPC",
            tags=builders.build_vpc_tags(
                component='thing1',
                deployment_identifier='gold',
                dependencies=['thing2-silver', 'thing3-bronze']))

        dependent_dependency_vpc_response = mocks.build_vpc_response_mock(
            name='Dependent Dependency VPC',
            tags=builders.build_vpc_tags(
                component='thing2',
                deployment_identifier='silver',
                dependencies=['thing1-gold']))
        standard_dependency_vpc_response = mocks.build_vpc_response_mock(
            name='Standard Dependency VPC',
            tags=builders.build_vpc_tags(
                component='thing3',
                deployment_identifier='bronze',
                dependencies=[]))

        standard_dependent_vpc_response = mocks.build_vpc_response_mock(
            name='Standard Dependent VPC',
            tags=builders.build_vpc_tags(
                component='thing4',
                deployment_identifier='lead',
                dependencies=['thing1-gold']))

        other_vpc_response = mocks.build_vpc_response_mock(
            name='Other VPC',
            tags=builders.build_vpc_tags(
                component='other-thing',
                deployment_identifier='copper',
                dependencies=[]))

        target_vpc = VPC(target_vpc_response, account_id, region)
        dependent_dependency_vpc = \
            VPC(dependent_dependency_vpc_response, account_id, region)
        standard_dependency_vpc = \
            VPC(standard_dependency_vpc_response, account_id, region)
        standard_dependent_vpc = \
            VPC(standard_dependent_vpc_response, account_id, region)

        ec2_gateway = mocks.EC2Gateway(account_id, region)
        ec2_gateways = mocks.EC2Gateways([ec2_gateway])
        logger = Mock(name="Logger")

        ec2_gateway.resource().vpcs.all = Mock(
            name='All VPCs',
            return_value=[
                dependent_dependency_vpc_response,
                target_vpc_response,
                standard_dependent_vpc_response,
                other_vpc_response,
                standard_dependency_vpc_response
            ])

        vpc_links = VPCLinks(ec2_gateways, logger)
        resolved_vpc_links = vpc_links.resolve_for(account_id, target_vpc_id)

        self.assertEqual(
            resolved_vpc_links,
            {
                VPCLink(
                    ec2_gateways,
                    logger,
                    between=[target_vpc, dependent_dependency_vpc],
                    routes=[[target_vpc, dependent_dependency_vpc],
                            [dependent_dependency_vpc, target_vpc]]
                ),
                VPCLink(
                    ec2_gateways,
                    logger,
                    between=[target_vpc, standard_dependency_vpc],
                    routes=[[target_vpc, standard_dependency_vpc]]
                ),
                VPCLink(
                    ec2_gateways,
                    logger,
                    between=[standard_dependent_vpc, target_vpc],
                    routes=[[standard_dependent_vpc, target_vpc]]
                )})

    def test_resolves_using_multiple_ec2_gateways(self):
        region_1 = randoms.region()
        region_2 = randoms.region()
        account_id_1 = randoms.account_id()
        account_id_2 = randoms.account_id()

        target_vpc_id = randoms.vpc_id()

        target_vpc_response = mocks.build_vpc_response_mock(
            id=target_vpc_id,
            name="Target VPC",
            tags=builders.build_vpc_tags(
                component='thing1',
                deployment_identifier='gold',
                dependencies=['thing2-silver', 'thing3-bronze']))

        dependent_dependency_vpc_response = mocks.build_vpc_response_mock(
            name='Dependent Dependency VPC',
            tags=builders.build_vpc_tags(
                component='thing2',
                deployment_identifier='silver',
                dependencies=['thing1-gold']))
        standard_dependency_vpc_response = mocks.build_vpc_response_mock(
            name='Standard Dependency VPC',
            tags=builders.build_vpc_tags(
                component='thing3',
                deployment_identifier='bronze',
                dependencies=[]))

        standard_dependent_vpc_response = mocks.build_vpc_response_mock(
            name='Standard Dependent VPC',
            tags=builders.build_vpc_tags(
                component='thing4',
                deployment_identifier='lead',
                dependencies=['thing1-gold']))

        other_vpc_response = mocks.build_vpc_response_mock(
            name='Other VPC',
            tags=builders.build_vpc_tags(
                component='other-thing',
                deployment_identifier='copper',
                dependencies=[]))

        target_vpc = VPC(target_vpc_response, account_id_1, region_1)
        dependent_dependency_vpc = \
            VPC(dependent_dependency_vpc_response, account_id_1, region_1)
        standard_dependency_vpc = \
            VPC(standard_dependency_vpc_response, account_id_2, region_2)
        standard_dependent_vpc = \
            VPC(standard_dependent_vpc_response, account_id_1, region_1)

        ec2_gateway_1 = mocks.EC2Gateway(account_id_1, region_1)
        ec2_gateway_2 = mocks.EC2Gateway(account_id_2, region_2)
        ec2_gateways = mocks.EC2Gateways([ec2_gateway_1, ec2_gateway_2])
        logger = Mock(name="Logger")

        ec2_gateway_1.resource().vpcs.all = Mock(
            name="All VPCs in account %s, region %s" % (account_id_1, region_1),
            return_value=[
                dependent_dependency_vpc_response,
                target_vpc_response,
                standard_dependent_vpc_response])
        ec2_gateway_2.resource().vpcs.all = Mock(
            name='All VPCs in account %s, region %s' % (account_id_2, region_2),
            return_value=[
                standard_dependency_vpc_response,
                other_vpc_response])

        vpc_links = VPCLinks(ec2_gateways, logger)
        resolved_vpc_links = vpc_links.resolve_for(account_id_1, target_vpc_id)

        self.assertEqual(
            resolved_vpc_links,
            {
                VPCLink(
                    ec2_gateways,
                    logger,
                    between=[target_vpc, dependent_dependency_vpc],
                    routes=[[target_vpc, dependent_dependency_vpc],
                            [dependent_dependency_vpc, target_vpc]]
                ),
                VPCLink(
                    ec2_gateways,
                    logger,
                    between=[target_vpc, standard_dependency_vpc],
                    routes=[[target_vpc, standard_dependency_vpc]]
                ),
                VPCLink(
                    ec2_gateways,
                    logger,
                    between=[standard_dependent_vpc, target_vpc],
                    routes=[[standard_dependent_vpc, target_vpc]]
                )
            })

    def test_resolves_no_duplicates(self):
        account_id = randoms.account_id()
        region = randoms.region()

        vpc1_id = randoms.vpc_id()

        vpc1_response = mocks.build_vpc_response_mock(
            name='VPC 1',
            id=vpc1_id,
            tags=builders.build_vpc_tags(
                component="thing1",
                deployment_identifier="gold",
                dependencies=["thing2-silver"]))
        vpc2_response = mocks.build_vpc_response_mock(
            name='VPC 2',
            tags=builders.build_vpc_tags(
                component='thing2',
                deployment_identifier="silver",
                dependencies=["thing1-gold"]))

        vpc1 = VPC(vpc1_response, account_id, region)
        vpc2 = VPC(vpc2_response, account_id, region)

        ec2_gateway = mocks.EC2Gateway(account_id, region)
        ec2_gateways = mocks.EC2Gateways([ec2_gateway])
        logger = Mock(name="Logger")

        ec2_gateway.resource().vpcs.all = Mock(
            name="All VPCs",
            return_value=[
                vpc1_response,
                vpc2_response])

        vpc_links = VPCLinks(ec2_gateways, logger)
        resolved_vpc_links = vpc_links. \
            resolve_for(account_id, vpc1_id)

        self.assertEqual(
            resolved_vpc_links,
            {
                VPCLink(
                    ec2_gateways,
                    logger,
                    between=[vpc1, vpc2],
                    routes=[[vpc1, vpc2],
                            [vpc2, vpc1]]
                )
            })

    def test_logs_found_target_vpc(self):
        account_id = randoms.account_id()
        region = randoms.region()
        vpc1_id = randoms.vpc_id()

        vpc1 = mocks.build_vpc_response_mock(
            name='VPC 1',
            id=vpc1_id,
            tags=builders.build_vpc_tags(
                component="thing1",
                deployment_identifier="gold",
                dependencies=["thing2-silver"]))
        vpc2 = mocks.build_vpc_response_mock(
            name='VPC 2',
            tags=builders.build_vpc_tags(
                component='thing2',
                deployment_identifier="silver",
                dependencies=[]))

        ec2_gateway = mocks.EC2Gateway(account_id, region)
        ec2_gateways = mocks.EC2Gateways([ec2_gateway])
        logger = Mock(name="Logger")

        ec2_gateway.resource().vpcs.all = Mock(
            name="All VPCs",
            return_value=[vpc1, vpc2])

        vpc_links = VPCLinks(ec2_gateways, logger)
        vpc_links.resolve_for(account_id, vpc1_id)

        logger.info.assert_any_call(
            "Computing VPC links for VPC with ID: '%s' "
            "in account with ID: '%s'.",
            vpc1.id, account_id)
        logger.info.assert_any_call(
            "Found target VPC with ID: '%s', component: '%s', "
            "deployment identifier: '%s' and dependencies: '%s'.",
            vpc1.id, 'thing1', 'gold', ['thing2-silver'])

    def test_logs_not_found_target_vpc(self):
        region = randoms.region()
        account_id = randoms.account_id()
        vpc1_id = randoms.vpc_id()

        vpc1 = mocks.build_vpc_response_mock(
            name='VPC 1',
            id=vpc1_id,
            tags=builders.build_vpc_tags(
                component="thing1",
                deployment_identifier="gold",
                dependencies=["thing2-silver"]))

        ec2_gateway = mocks.EC2Gateway(account_id, region)
        ec2_gateways = mocks.EC2Gateways([ec2_gateway])
        logger = Mock(name="Logger")

        ec2_gateway.resource().vpcs.all = Mock(
            name="All VPCs",
            return_value=[])

        vpc_links = VPCLinks(ec2_gateways, logger)
        vpc_links.resolve_for(account_id, vpc1_id)

        logger.info.assert_any_call(
            "No VPC found with ID: '%s'. Aborting.", vpc1.id)

    def test_resolves_empty_set_for_missing_target_vpc(self):
        region = randoms.region()
        account_id = randoms.account_id()
        vpc1_id = randoms.vpc_id()

        ec2_gateway = mocks.EC2Gateway(account_id, region)
        ec2_gateways = mocks.EC2Gateways([ec2_gateway])
        logger = Mock(name="Logger")

        ec2_gateway.resource().vpcs.all = Mock(
            name="All VPCs",
            return_value=[])

        vpc_links = VPCLinks(ec2_gateways, logger)
        resolved_vpc_links = vpc_links.resolve_for(
            account_id, vpc1_id)

        self.assertEqual(resolved_vpc_links, set())

    def test_ignores_missing_dependencies(self):
        account_id = randoms.account_id()
        region = randoms.region()
        vpc1_id = randoms.vpc_id()

        vpc_1_response = mocks.build_vpc_response_mock(
            name='VPC 1',
            id=vpc1_id,
            tags=builders.build_vpc_tags(
                component="thing1",
                deployment_identifier="gold",
                dependencies=["thing2-silver", "thing3-bronze"]))
        vpc_2_response = mocks.build_vpc_response_mock(
            name='VPC 2',
            tags=builders.build_vpc_tags(
                component="thing2",
                deployment_identifier="silver",
                dependencies=[]))

        vpc_1 = VPC(vpc_1_response, account_id, region)
        vpc_2 = VPC(vpc_2_response, account_id, region)

        ec2_gateway = mocks.EC2Gateway(account_id, region)
        ec2_gateways = mocks.EC2Gateways([ec2_gateway])
        logger = Mock(name="Logger")

        ec2_gateway.resource().vpcs.all = Mock(
            name="All VPCs",
            return_value=[vpc_1_response, vpc_2_response])

        vpc_links = VPCLinks(ec2_gateways, logger)
        resolved_vpc_links = vpc_links.resolve_for(
            account_id, vpc1_id)

        self.assertEqual(len(resolved_vpc_links), 1)
        self.assertEqual(
            resolved_vpc_links,
            {
                VPCLink(
                    ec2_gateways,
                    logger,
                    between=[vpc_1, vpc_2],
                    routes=[[vpc_1, vpc_2]])
            })

    def test_logs_dependency_vpcs(self):
        region = randoms.region()
        account_id = randoms.region()

        target_vpc_id = randoms.vpc_id()
        dependency_vpc1_id = randoms.vpc_id()
        dependency_vpc2_id = randoms.vpc_id()

        target_vpc = mocks.build_vpc_response_mock(
            name="Target VPC",
            id=target_vpc_id,
            tags=builders.build_vpc_tags(
                component="thing1",
                deployment_identifier="gold",
                dependencies=["thing2-silver", "thing3-bronze"]))

        dependency_vpc1 = mocks.build_vpc_response_mock(
            name="Dependency VPC 1",
            id=dependency_vpc1_id,
            tags=builders.build_vpc_tags(
                component="thing2",
                deployment_identifier="silver",
                dependencies=[]))
        dependency_vpc2 = mocks.build_vpc_response_mock(
            name="Dependency VPC 2",
            id=dependency_vpc2_id,
            tags=builders.build_vpc_tags(
                component="thing3",
                deployment_identifier="bronze",
                dependencies=[]))

        ec2_gateway = mocks.EC2Gateway(account_id, region)
        ec2_gateways = mocks.EC2Gateways([ec2_gateway])
        logger = Mock(name="Logger")

        ec2_gateway.resource().vpcs.all = Mock(
            name="All VPCs",
            return_value=[
                dependency_vpc1,
                target_vpc,
                dependency_vpc2])

        vpc_links = VPCLinks(ec2_gateways, logger)
        vpc_links.resolve_for(account_id, target_vpc_id)

        logger.info.assert_any_call(
            "Found dependency VPCs: [%s]",
            "'thing2-silver':'%s', 'thing3-bronze':'%s'" % (
                dependency_vpc1_id, dependency_vpc2_id))

    def test_logs_dependent_vpcs(self):
        region = randoms.region()
        account_id = randoms.region()

        target_vpc_id = randoms.vpc_id()
        dependent_vpc1_id = randoms.vpc_id()
        dependent_vpc2_id = randoms.vpc_id()

        target_vpc = mocks.build_vpc_response_mock(
            name="Target VPC",
            id=target_vpc_id,
            tags=builders.build_vpc_tags(
                component="thing1",
                deployment_identifier="gold",
                dependencies=[]))

        dependent_vpc1 = mocks.build_vpc_response_mock(
            name="Dependent VPC 1",
            id=dependent_vpc1_id,
            tags=builders.build_vpc_tags(
                component="thing2",
                deployment_identifier="silver",
                dependencies=["thing1-gold"]))
        dependent_vpc2 = mocks.build_vpc_response_mock(
            name="Dependent VPC 2",
            id=dependent_vpc2_id,
            tags=builders.build_vpc_tags(
                component="thing3",
                deployment_identifier="bronze",
                dependencies=["thing1-gold"]))

        ec2_gateway = mocks.EC2Gateway(account_id, region)
        ec2_gateways = mocks.EC2Gateways([ec2_gateway])
        logger = Mock(name="Logger")

        ec2_gateway.resource().vpcs.all = Mock(
            name="All VPCs",
            return_value=[
                dependent_vpc1,
                target_vpc,
                dependent_vpc2])

        vpc_links = VPCLinks(ec2_gateways, logger)
        vpc_links.resolve_for(account_id, target_vpc_id)

        logger.info.assert_any_call(
            "Found dependent VPCs: [%s]",
            "'thing2-silver':'%s', 'thing3-bronze':'%s'" % (
                dependent_vpc1_id, dependent_vpc2_id))
