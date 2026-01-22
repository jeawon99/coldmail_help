"""
Stage 5 - Import & Syntax Check
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coldmail_project.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

# Import 테스트
try:
    from campaigns.models import Campaign, CampaignTarget
    from campaigns.serializers import (
        CampaignSerializer,
        CampaignListSerializer,
        CampaignTargetSerializer,
        FreezeTargetsRequestSerializer,
        FreezeTargetsResponseSerializer,
        TargetAddRequestSerializer,
        TargetRemoveRequestSerializer
    )
    from campaigns.views import CampaignViewSet
    
    print("✅ 모든 Import 성공!")
    print("\nModels:")
    print(f"  - Campaign: {Campaign._meta.db_table}")
    print(f"  - CampaignTarget: {CampaignTarget._meta.db_table}")
    
    print("\nSerializers:")
    print(f"  - CampaignSerializer")
    print(f"  - CampaignListSerializer")
    print(f"  - CampaignTargetSerializer")
    print(f"  - FreezeTargetsRequestSerializer")
    print(f"  - FreezeTargetsResponseSerializer")
    print(f"  - TargetAddRequestSerializer")
    print(f"  - TargetRemoveRequestSerializer")
    
    print("\nViewSets:")
    print(f"  - CampaignViewSet")
    
    print("\nCampaignViewSet Actions:")
    actions = [
        method for method in dir(CampaignViewSet)
        if not method.startswith('_') and callable(getattr(CampaignViewSet, method))
    ]
    for action in ['freeze_targets', 'targets_list', 'targets_add', 'targets_remove', 'start_campaign', 'pause_campaign', 'finish_campaign']:
        if action in actions:
            print(f"  ✅ {action}")
        else:
            print(f"  ❌ {action} - NOT FOUND")
    
    # 필드 확인
    print("\nCampaign 필드:")
    for field in Campaign._meta.fields:
        print(f"  - {field.name}: {field.__class__.__name__}")
    
    print("\nCampaignTarget 필드:")
    for field in CampaignTarget._meta.fields:
        print(f"  - {field.name}: {field.__class__.__name__}")
    
    print("\n✅ Stage 5 구현 완료!")
    
except ImportError as e:
    print(f"❌ Import 실패: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ 에러: {e}")
    import traceback
    traceback.print_exc()
