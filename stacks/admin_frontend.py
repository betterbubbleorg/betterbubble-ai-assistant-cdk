from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3_deployment as s3_deployment,
    RemovalPolicy,
    CfnOutput
)
from constructs import Construct
from typing import Optional

class AdminFrontendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: dict, stacks: Optional[dict] = None, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # S3 bucket for admin portal
        self.admin_bucket = s3.Bucket(
            self, "AdminBucket",
            bucket_name=f"{config.generate_stack_name('admin-portal')}",
            website_index_document="admin.html",
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
        
        # CloudFront distribution for admin portal
        self.admin_distribution = cloudfront.Distribution(
            self, "AdminDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin(self.admin_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED
            ),
            default_root_object="admin.html"
        )
        
        # Deploy admin portal files
        self.admin_deployment = s3_deployment.BucketDeployment(
            self, "AdminDeployment",
            sources=[s3_deployment.Source.asset("templates")],
            destination_bucket=self.admin_bucket,
            distribution=self.admin_distribution,
            distribution_paths=["/*"]
        )
        
        # Outputs
        CfnOutput(
            self, "AdminCloudFrontDomainName",
            value=self.admin_distribution.distribution_domain_name,
            description="CloudFront domain name for admin portal"
        )
        
        CfnOutput(
            self, "AdminCloudFrontUrl",
            value="https://" + self.admin_distribution.distribution_domain_name,
            description="CloudFront URL for admin portal"
        )
