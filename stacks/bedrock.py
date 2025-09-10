"""
AI Services Stack for AI Personal Assistant
Creates Bedrock foundation models and related AI services.
"""

from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_bedrock as bedrock,
    aws_kms as kms
)
from constructs import Construct
from typing import Optional


class BedrockStack(Stack):
    """Amazon Bedrock and AI services for personal assistant."""

    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create KMS key for Bedrock encryption
        self.bedrock_key = kms.Key(
            self, "BedrockEncryptionKey",
            description="KMS key for Bedrock model encryption",
            enable_key_rotation=True
        )

        # Create IAM role for Bedrock access
        self.bedrock_role = iam.Role(
            self, "BedrockExecutionRole",
            role_name="BetterBubble-AI-BedrockRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add Bedrock permissions
        self.bedrock_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:GetFoundationModel",
                    "bedrock:ListFoundationModels"
                ],
                resources=["*"]
            )
        )

        # Add KMS permissions for encryption
        self.bedrock_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "kms:Decrypt",
                    "kms:GenerateDataKey"
                ],
                resources=[self.bedrock_key.key_arn]
            )
        )

        # Note: Inference profiles need to be created via AWS Console or CLI
        # as CDK doesn't have direct support for creating inference profiles
        # For now, we'll use the direct model ID approach with proper error handling
