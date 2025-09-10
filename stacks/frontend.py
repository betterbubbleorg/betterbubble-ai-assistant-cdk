"""
Frontend Stack for AI Personal Assistant
Creates a simple HTML chatbot interface hosted on S3 with CloudFront.
"""

from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
    aws_certificatemanager as acm,
    RemovalPolicy
)
from constructs import Construct
from typing import Optional
import os
from jinja2 import Template


class FrontendStack(Stack):
    """Simple HTML chatbot interface hosted on S3 with CloudFront."""

    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        config: dict,
        stacks: dict,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Get API Gateway URL and Cognito info from stacks
        api_url = ""
        cognito_user_pool_id = ""
        cognito_client_id = ""
        cognito_identity_pool_id = ""
        
        if stacks and 'lambda' in stacks:
            api_url = stacks['lambda'].api.url
        
        if stacks and 'cognito' in stacks:
            cognito_user_pool_id = stacks['cognito'].user_pool.user_pool_id
            cognito_client_id = stacks['cognito'].user_pool_client.user_pool_client_id
            cognito_identity_pool_id = stacks['cognito'].identity_pool.ref

        # Create S3 bucket for hosting
        self.hosting_bucket = s3.Bucket(
            self, "ChatbotHostingBucket",
            bucket_name=f"betterbubble-chatbot-{self.account}-{self.region}",
            website_index_document="index.html",
            website_error_document="error.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                block_public_policy=False,
                ignore_public_acls=False,
                restrict_public_buckets=False
            ),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Create hosted zone for betterbubble.org
        self.hosted_zone = route53.HostedZone(
            self, "BetterBubbleZone",
            zone_name="betterbubble.org",
            comment="Better Bubble AI Personal Assistant domain"
        )

        # Create SSL certificate for custom domain
        self.certificate = acm.Certificate(
            self, "ChatbotCertificate",
            domain_name="chatbot.betterbubble.org",
            validation=acm.CertificateValidation.from_dns(self.hosted_zone)
        )

        # Create CloudFront distribution with custom domain
        self.distribution = cloudfront.Distribution(
            self, "ChatbotDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin(self.hosting_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED
            ),
            default_root_object="index.html",
            domain_names=["chatbot.betterbubble.org"],
            certificate=self.certificate,
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html"
                )
            ]
        )

        # Create Route53 record for custom domain
        self.domain_record = route53.ARecord(
            self, "ChatbotDomainRecord",
            zone=self.hosted_zone,
            record_name="chatbot",
            target=route53.RecordTarget.from_alias(
                route53_targets.CloudFrontTarget(self.distribution)
            )
        )

        # Load and render Jinja2 template
        template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'chatbot.html')
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        template = Template(template_content)
        html_content = template.render(
            cognito_user_pool_id=cognito_user_pool_id,
            cognito_client_id=cognito_client_id,
            cognito_identity_pool_id=cognito_identity_pool_id,
            api_url=api_url
        )

        # Deploy HTML content to S3
        s3_deployment.BucketDeployment(
            self, "ChatbotDeployment",
            sources=[s3_deployment.Source.data("index.html", html_content)],
            destination_bucket=self.hosting_bucket,
            distribution=self.distribution,
            distribution_paths=["/*"]
        )
