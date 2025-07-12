from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    CfnOutput,
    Duration
)
from constructs import Construct

class PerformanceOptimizationStack(Stack):
    """
    성능 최적화 스택 - 기본 모니터링 및 알람
    """
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # 1. SNS 토픽 생성 (알람용)
        self.alarm_topic = sns.Topic(
            self, "AlarmTopic",
            display_name="TITLE-NOMICS 알람",
            topic_name="title-nomics-alarms"
        )
        
        # 2. 기본 CloudWatch 대시보드 생성
        self.create_basic_dashboard()
        
        # 3. 출력값 생성
        self.create_outputs()
    
    def create_basic_dashboard(self):
        """기본 CloudWatch 대시보드 생성"""
        
        self.dashboard = cloudwatch.Dashboard(
            self, "PerformanceDashboard",
            dashboard_name="TITLE-NOMICS-Performance",
            default_interval=Duration.hours(1)
        )
        
        # Lambda 함수 메트릭 위젯 추가
        self.dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Lambda 함수 실행 시간",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Duration",
                        dimensions_map={"FunctionName": "bedrock-diy-generate"},
                        statistic="Average"
                    )
                ],
                width=12,
                height=6
            )
        )
        
        self.dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Lambda 함수 오류율",
                left=[
                    cloudwatch.Metric(
                        namespace="AWS/Lambda",
                        metric_name="Errors",
                        dimensions_map={"FunctionName": "bedrock-diy-generate"},
                        statistic="Sum"
                    )
                ],
                width=12,
                height=6
            )
        )
    
    def create_outputs(self):
        """출력값 생성"""
        
        CfnOutput(
            self, "AlarmTopicArn",
            value=self.alarm_topic.topic_arn,
            description="알람 SNS 토픽 ARN",
            export_name="AlarmTopicArn"
        )
        
        CfnOutput(
            self, "DashboardUrl",
            value=f"https://console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={self.dashboard.dashboard_name}",
            description="CloudWatch 대시보드 URL",
            export_name="DashboardUrl"
        ) 