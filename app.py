#!/usr/bin/env python3
"""
Better Bubble AI Personal Assistant - CDK App
Main entry point for the AI Personal Assistant infrastructure.
"""

import os
import sys
import aws_cdk as cdk

# Add common constructs to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common-constructs'))

from environment import Config
from stacks.dynamodb import DynamoDBStack
from stacks.cognito import CognitoStack
from stacks.awslambda import LambdaStack
from stacks.frontend import FrontendStack
from stacks.bedrock import BedrockStack
from stacks.cloudwatch import CloudWatchStack

# Create CDK App with cross-region references enabled
app = cdk.App()
app.node.set_context("crossRegionReferences", True)

# Load configuration
conf_path = os.path.join(os.path.dirname(__file__), 'conf')
config, cdk_env = Config.create(conf_path)

# Create global environment (us-east-1) for services that require it
global_cdk_env = config.environment(region='us-east-1')

# Create stacks dictionary to hold all stage stacks
stacks = {}

# Create stacks for each environment
for environment_name in config.stages:
    # Load environment-specific configuration with stack name generation
    stage_config = config.load_stage_config(environment_name)
    
    # Create stage-specific stacks dictionary
    stage_stacks = {}
    
    # Create base stacks (no dependencies)
    stage_stacks['dynamodb'] = DynamoDBStack(
        app, stage_config.generate_stack_name('dynamodb'),
        env=cdk_env, config=stage_config
    )
    
    stage_stacks['cognito'] = CognitoStack(
        app, stage_config.generate_stack_name('cognito'),
        env=cdk_env, config=stage_config
    )
    
    stage_stacks['bedrock'] = BedrockStack(
        app, stage_config.generate_stack_name('bedrock'),
        env=cdk_env, config=stage_config
    )
    
    # Create dependent stacks (with stacks reference)
    stage_stacks['lambda'] = LambdaStack(
        app, stage_config.generate_stack_name('lambda'),
        env=cdk_env, config=stage_config, stacks=stage_stacks
    )
    
    stage_stacks['frontend'] = FrontendStack(
        app, stage_config.generate_stack_name('frontend'),
        env=cdk_env, config=stage_config, stacks=stage_stacks
    )
    
    stage_stacks['cloudwatch'] = CloudWatchStack(
        app, stage_config.generate_stack_name('cloudwatch'),
        env=cdk_env, config=stage_config, stacks=stage_stacks
    )
    
    # Add stage stacks to main stacks dictionary
    stacks[environment_name] = stage_stacks

# Synthesize the app
app.synth()
