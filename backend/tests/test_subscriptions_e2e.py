"""Comprehensive E2E Test Suite for Merchant Subscription System.

Tiers:
- Tier 1: Feature Coverage (Features 1-7: Signup Trial, Dynamic Eval, Admin View, Update, Extend, Gating, Non-Upload)
- Tier 2: Boundary & Corner Cases (Boundary dates, timestamps, zero durations, past extensions, precision)
- Tier 3: Cross-Feature Combinations (Pairwise interactions across state transitions and roles)
- Tier 4: Real-World Scenarios (Full lifecycles, suspensions, multi-staff operations, cumulative timelines)
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from tests.e2e_subscriptions.helpers import (
    prepare_schema,
    set_auto_approve,
    set_auto_approve_kyc,
)

# Re-export Tier 1 Test Classes
from tests.e2e_subscriptions.t1_signup_trial import (
    TestTier1SignupTrial,
    TestTier1DynamicEval,
)
from tests.e2e_subscriptions.t1_admin_endpoints import (
    TestTier1AdminView,
    TestTier1AdminUpdate,
    TestTier1AdminExtend,
)
from tests.e2e_subscriptions.t1_gating_ungated import (
    TestTier1ContentGating,
    TestTier1NonUploadPreservation,
)

# Re-export Tier 2 Boundary Test Classes
from tests.e2e_subscriptions.t2_trial_admin_boundaries import (
    TestTier2TrialBoundaries,
    TestTier2DynamicEvalBoundaries,
    TestTier2AdminViewBoundaries,
    TestTier2AdminUpdateBoundaries,
    TestTier2AdminExtendBoundaries,
)
from tests.e2e_subscriptions.t2_gating_ungated_boundaries import (
    TestTier2GatingBoundaries,
    TestTier2NonUploadBoundaries,
)

# Re-export Tier 3 Cross-Feature Combination Test Classes
from tests.e2e_subscriptions.t3_combinations import (
    TestTier3CrossFeatureCombinations,
)

# Re-export Tier 4 Real-World Scenario Test Classes
from tests.e2e_subscriptions.t4_lifecycle import (
    TestTier4RealWorldScenarios,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=True)
async def init_db():
    """Initializes database schema and enables auto-approve for KYC and reels."""
    await prepare_schema()
    await set_auto_approve(True)
    await set_auto_approve_kyc(True)
    yield
    await set_auto_approve(False)
    await set_auto_approve_kyc(False)


@pytest_asyncio.fixture
async def client():
    """Async HTTP test client against the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
