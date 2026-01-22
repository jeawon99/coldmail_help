from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from django.core.mail import send_mail
from django.conf import settings
from .serializers import SendEmailSerializer, EmailSerializer
import imaplib
import email
from email.header import decode_header


class SendEmailAPIView(APIView):
    """
    메일 발송 API 엔드포인트
    
    POST: SMTP 연결 테스트 및 메일 발송
    """
    
    @extend_schema(
        summary="메일 발송",
        description="SMTP 서버를 통해 메일을 발송합니다. (개발 환경에서는 콘솔에 출력됩니다)",
        request=SendEmailSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'errors': {'type': 'object'},
                }
            }
        },
        examples=[
            OpenApiExample(
                'Request Example',
                value={
                    'to_email': 'recipient@example.com',
                    'subject': '테스트 메일',
                    'content': '안녕하세요, 이것은 테스트 메일입니다.'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'message': '메일이 성공적으로 발송되었습니다.'
                },
                response_only=True,
            )
        ]
    )
    def post(self, request):
        """메일 발송"""
        serializer = SendEmailSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 메일 발송
            send_mail(
                subject=serializer.validated_data['subject'],
                message=serializer.validated_data['content'],
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[serializer.validated_data['to_email']],
                fail_silently=False,
            )
            
            return Response({
                'success': True,
                'message': '메일이 성공적으로 발송되었습니다.'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'메일 발송 실패: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReceiveEmailAPIView(APIView):
    """
    메일 수신 조회 API 엔드포인트
    
    GET: IMAP을 통해 수신 메일함 조회
    """
    
    @extend_schema(
        summary="수신 메일 조회",
        description="IMAP 서버에서 수신된 메일 목록을 가져옵니다.",
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                location=OpenApiParameter.QUERY,
                description='조회할 메일 개수 (기본값: 10)',
                required=False,
            ),
            OpenApiParameter(
                name='mailbox',
                type=str,
                location=OpenApiParameter.QUERY,
                description='조회할 메일함 (기본값: INBOX)',
                required=False,
            ),
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'count': {'type': 'integer'},
                    'emails': {'type': 'array', 'items': {'$ref': '#/components/schemas/Email'}},
                }
            }
        },
        examples=[
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'count': 2,
                    'emails': [
                        {
                            'uid': '1',
                            'from_email': 'sender@example.com',
                            'subject': '테스트 메일',
                            'date': 'Wed, 22 Jan 2026 10:00:00 +0900',
                            'body': '메일 본문 내용...'
                        }
                    ]
                },
                response_only=True,
            )
        ]
    )
    def get(self, request):
        """수신 메일 조회"""
        limit = int(request.query_params.get('limit', 10))
        mailbox_name = request.query_params.get('mailbox', 'INBOX')
        
        try:
            # IMAP 연결
            if settings.IMAP_EMAIL_USE_SSL:
                mail = imaplib.IMAP4_SSL(settings.IMAP_EMAIL_HOST, settings.IMAP_EMAIL_PORT)
            else:
                mail = imaplib.IMAP4(settings.IMAP_EMAIL_HOST, settings.IMAP_EMAIL_PORT)
            
            # 로그인
            mail.login(settings.IMAP_EMAIL_USER, settings.IMAP_EMAIL_PASSWORD)
            
            # 메일함 선택
            mail.select(mailbox_name)
            
            # 모든 메일 검색
            status_code, messages = mail.search(None, 'ALL')
            email_ids = messages[0].split()
            
            # 최신 메일부터 limit 개수만큼 가져오기
            email_ids = email_ids[-limit:][::-1]  # 역순으로 정렬
            
            emails = []
            for email_id in email_ids:
                # 메일 가져오기
                status_code, msg_data = mail.fetch(email_id, '(RFC822)')
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # 제목 디코딩
                        subject = self._decode_header(msg.get('Subject', ''))
                        
                        # 발신자 디코딩
                        from_email = self._decode_header(msg.get('From', ''))
                        
                        # 날짜
                        date = msg.get('Date', '')
                        
                        # 본문 추출
                        body = self._get_email_body(msg)
                        
                        emails.append({
                            'uid': email_id.decode(),
                            'from_email': from_email,
                            'subject': subject,
                            'date': date,
                            'body': body[:500] if body else ''  # 본문 500자까지만
                        })
            
            # 연결 종료
            mail.close()
            mail.logout()
            
            return Response({
                'success': True,
                'count': len(emails),
                'emails': emails
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'메일 조회 실패: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _decode_header(self, header_value):
        """메일 헤더 디코딩"""
        if not header_value:
            return ''
        
        decoded_parts = decode_header(header_value)
        decoded_string = ''
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    decoded_string += part.decode(encoding or 'utf-8')
                except:
                    decoded_string += part.decode('utf-8', errors='ignore')
            else:
                decoded_string += part
        
        return decoded_string
    
    def _get_email_body(self, msg):
        """메일 본문 추출"""
        body = ''
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition'))
                
                if content_type == 'text/plain' and 'attachment' not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                pass
        
        return body
