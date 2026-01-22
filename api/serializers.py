from rest_framework import serializers


class SendEmailSerializer(serializers.Serializer):
    """메일 발송용 시리얼라이저"""
    to_email = serializers.EmailField(help_text="받는 사람 이메일 주소")
    subject = serializers.CharField(max_length=200, help_text="메일 제목")
    content = serializers.CharField(help_text="메일 내용")


class EmailSerializer(serializers.Serializer):
    """수신 메일 조회용 시리얼라이저"""
    uid = serializers.CharField(help_text="메일 고유 ID")
    from_email = serializers.CharField(help_text="발신자 이메일")
    subject = serializers.CharField(help_text="메일 제목")
    date = serializers.CharField(help_text="수신 날짜")
    body = serializers.CharField(help_text="메일 본문", required=False)
