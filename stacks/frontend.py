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
    aws_certificatemanager as acm,
    RemovalPolicy,
    CfnOutput
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
            bucket_name=f"{config.generate_stack_name('chatbot')}-{self.account}-{self.region}",
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

        # Import validated certificate from us-east-1
        self.certificate = acm.Certificate.from_certificate_arn(
            self, "ImportedCertificate",
            certificate_arn="arn:aws:acm:us-east-1:166199670697:certificate/7ca9242f-38c1-42d8-96aa-3409d79d7322"
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

        # Export CloudFront information
        CfnOutput(
            self, "CloudFrontDomainName",
            value=self.distribution.distribution_domain_name,
            description="CloudFront distribution domain name"
        )
        
        CfnOutput(
            self, "CustomDomainUrl",
            value="https://chatbot.betterbubble.org",
            description="Custom domain URL for the chatbot interface"
        )
        
        CfnOutput(
            self, "DNSInstructions",
            value=f"Create CNAME record: chatbot.betterbubble.org -> {self.distribution.distribution_domain_name}",
            description="DNS configuration instructions"
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

        # Load and render debug template
        debug_template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'debug_session.html')
        with open(debug_template_path, 'r') as f:
            debug_template_content = f.read()
        
        debug_template = Template(debug_template_content)
        debug_html_content = debug_template.render(
            cognito_user_pool_id=cognito_user_pool_id,
            cognito_client_id=cognito_client_id,
            cognito_identity_pool_id=cognito_identity_pool_id,
            api_url=api_url
        )

        # Deploy HTML content to S3
        s3_deployment.BucketDeployment(
            self, "ChatbotDeployment",
            sources=[
                s3_deployment.Source.data("index.html", html_content),
                s3_deployment.Source.data("debug_session.html", debug_html_content)
            ],
            destination_bucket=self.hosting_bucket,
            distribution=self.distribution,
            distribution_paths=["/*"]
        )
