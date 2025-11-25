"""
Production Environment Configuration Validator

Validates that all security-critical environment variables are properly configured
before deployment to production.
"""

import os
import sys
import re
from typing import List, Tuple
from dotenv import load_dotenv


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ProductionConfigValidator:
    """Validates production environment configuration."""
    
    def __init__(self, env_file: str = ".env"):
        """Initialize validator and load environment."""
        self.env_file = env_file
        load_dotenv(env_file, override=True)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
    
    def validate_jwt_secret(self) -> bool:
        """Validate JWT secret key is strong."""
        jwt_secret = os.getenv('JWT_SECRET_KEY', '')
        
        if not jwt_secret:
            self.errors.append("❌ JWT_SECRET_KEY not set")
            return False
        
        # Check for default/weak values
        weak_values = [
            'your-secret-key-change-this-in-production',
            'secret',
            'dev',
            'test',
            'change-me'
        ]
        
        if jwt_secret.lower() in weak_values:
            self.errors.append(
                f"❌ JWT_SECRET_KEY is set to default/weak value: {jwt_secret}"
            )
            return False
        
        # Check length (should be at least 32 characters)
        if len(jwt_secret) < 32:
            self.errors.append(
                f"❌ JWT_SECRET_KEY too short ({len(jwt_secret)} chars). "
                f"Minimum 32 characters recommended."
            )
            return False
        
        # Check complexity (should have letters and numbers)
        has_letters = any(c.isalpha() for c in jwt_secret)
        has_numbers = any(c.isdigit() for c in jwt_secret)
        
        if not (has_letters and has_numbers):
            self.warnings.append(
                "⚠️  JWT_SECRET_KEY should contain both letters and numbers"
            )
        
        self.passed.append(f"✅ JWT_SECRET_KEY: {len(jwt_secret)} chars, looks strong")
        return True
    
    def validate_cors_origins(self) -> bool:
        """Validate CORS origins are properly restricted."""
        cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', '')
        mturk_env = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
        
        if not cors_origins:
            self.errors.append("❌ CORS_ALLOWED_ORIGINS not set")
            return False
        
        # Check for wildcard
        if '*' in cors_origins:
            self.errors.append(
                "❌ CORS_ALLOWED_ORIGINS contains wildcard '*'. "
                "This is a CRITICAL security vulnerability!"
            )
            return False
        
        origins = [o.strip() for o in cors_origins.split(',')]
        
        # In production, all origins should be HTTPS
        if mturk_env == 'production':
            for origin in origins:
                if origin.startswith('http://') and 'localhost' not in origin:
                    self.errors.append(
                        f"❌ HTTP origin in production: {origin}. "
                        f"All production origins must use HTTPS."
                    )
                    return False
        
        self.passed.append(f"✅ CORS_ALLOWED_ORIGINS: {len(origins)} origins configured")
        for origin in origins:
            self.passed.append(f"   - {origin}")
        return True
    
    def validate_mturk_config(self) -> bool:
        """Validate MTurk configuration."""
        aws_access_key = os.getenv('AWS_ACCESS_KEY_ID', '')
        aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', '')
        mturk_env = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
        external_url = os.getenv('EXTERNAL_URL', '')
        
        success = True
        
        # Check AWS credentials exist
        if not aws_access_key:
            self.errors.append("❌ AWS_ACCESS_KEY_ID not set")
            success = False
        elif len(aws_access_key) < 16:
            self.errors.append(f"❌ AWS_ACCESS_KEY_ID too short: {len(aws_access_key)} chars")
            success = False
        else:
            self.passed.append(f"✅ AWS_ACCESS_KEY_ID: {aws_access_key[:4]}...{aws_access_key[-4:]}")
        
        if not aws_secret_key:
            self.errors.append("❌ AWS_SECRET_ACCESS_KEY not set")
            success = False
        elif len(aws_secret_key) < 32:
            self.errors.append(f"❌ AWS_SECRET_ACCESS_KEY too short: {len(aws_secret_key)} chars")
            success = False
        else:
            self.passed.append(f"✅ AWS_SECRET_ACCESS_KEY: {aws_secret_key[:4]}...{aws_secret_key[-4:]}")
        
        # Check MTurk environment
        if mturk_env not in ['sandbox', 'production']:
            self.errors.append(
                f"❌ MTURK_ENVIRONMENT must be 'sandbox' or 'production', got: {mturk_env}"
            )
            success = False
        else:
            self.passed.append(f"✅ MTURK_ENVIRONMENT: {mturk_env}")
        
        # Check external URL
        if not external_url:
            self.errors.append("❌ EXTERNAL_URL not set")
            success = False
        elif mturk_env == 'production' and not external_url.startswith('https://'):
            self.errors.append(
                f"❌ EXTERNAL_URL must be HTTPS in production, got: {external_url}"
            )
            success = False
        else:
            self.passed.append(f"✅ EXTERNAL_URL: {external_url}")
        
        return success
    
    def validate_payment_limits(self) -> bool:
        """Validate payment limit configuration."""
        base_pay = os.getenv('MTURK_BASE_PAY', '0.05')
        max_bonus = os.getenv('MTURK_MAX_BONUS', '0.05')
        min_cashout = os.getenv('MINIMUM_CASHOUT_AMOUNT', '2.00')
        
        try:
            base_pay_decimal = float(base_pay)
            max_bonus_decimal = float(max_bonus)
            min_cashout_decimal = float(min_cashout)
            
            # Sanity checks
            if base_pay_decimal <= 0:
                self.errors.append(f"❌ MTURK_BASE_PAY must be positive, got: {base_pay}")
                return False
            
            if max_bonus_decimal < 0:
                self.errors.append(f"❌ MTURK_MAX_BONUS cannot be negative, got: {max_bonus}")
                return False
            
            if min_cashout_decimal < 0.01:
                self.errors.append(f"❌ MINIMUM_CASHOUT_AMOUNT too low, got: {min_cashout}")
                return False
            
            total_max_payment = base_pay_decimal + max_bonus_decimal
            
            self.passed.append(f"✅ MTURK_BASE_PAY: ${base_pay}")
            self.passed.append(f"✅ MTURK_MAX_BONUS: ${max_bonus}")
            self.passed.append(f"✅ Maximum payment per worker: ${total_max_payment:.2f}")
            self.passed.append(f"✅ MINIMUM_CASHOUT_AMOUNT: ${min_cashout}")
            
            return True
            
        except ValueError as e:
            self.errors.append(f"❌ Invalid payment configuration: {e}")
            return False
    
    def validate_database_config(self) -> bool:
        """Validate database configuration."""
        database_url = os.getenv('DATABASE_URL', '')
        mturk_env = os.getenv('MTURK_ENVIRONMENT', 'sandbox')
        
        if not database_url:
            self.errors.append("❌ DATABASE_URL not set")
            return False
        
        # In production, should use PostgreSQL, not SQLite
        if mturk_env == 'production':
            if 'sqlite' in database_url.lower():
                self.errors.append(
                    "❌ SQLite database not recommended for production. "
                    "Use PostgreSQL for better concurrency and reliability."
                )
                return False
            
            if not database_url.startswith('postgresql'):
                self.warnings.append(
                    f"⚠️  DATABASE_URL doesn't start with 'postgresql': {database_url[:30]}..."
                )
        
        self.passed.append(f"✅ DATABASE_URL configured: {database_url[:30]}...")
        return True
    
    def validate_completion_key_secret(self) -> bool:
        """Validate completion key signing secret."""
        completion_secret = os.getenv('JWT_COMPLETION_SECRET', '')
        
        if not completion_secret:
            self.errors.append("❌ JWT_COMPLETION_SECRET not set")
            return False
        
        weak_values = ['your-completion-key-secret-change-this', 'secret', 'test']
        if completion_secret.lower() in weak_values:
            self.errors.append(
                f"❌ JWT_COMPLETION_SECRET is default/weak value"
            )
            return False
        
        if len(completion_secret) < 32:
            self.errors.append(
                f"❌ JWT_COMPLETION_SECRET too short: {len(completion_secret)} chars"
            )
            return False
        
        self.passed.append(f"✅ JWT_COMPLETION_SECRET: {len(completion_secret)} chars")
        return True
    
    def validate_all(self) -> Tuple[bool, List[str], List[str], List[str]]:
        """
        Run all validations.
        
        Returns:
            Tuple of (all_passed, errors, warnings, passed_checks)
        """
        print("\n" + "=" * 70)
        print("🔒 PRODUCTION CONFIGURATION SECURITY VALIDATOR")
        print("=" * 70)
        print(f"Environment file: {self.env_file}")
        print(f"MTurk environment: {os.getenv('MTURK_ENVIRONMENT', 'not set')}")
        print("")
        
        # Run all validations
        validations = [
            ("JWT Secret Key", self.validate_jwt_secret),
            ("CORS Origins", self.validate_cors_origins),
            ("MTurk Configuration", self.validate_mturk_config),
            ("Payment Limits", self.validate_payment_limits),
            ("Database Configuration", self.validate_database_config),
            ("Completion Key Secret", self.validate_completion_key_secret),
        ]
        
        results = []
        for name, validator in validations:
            print(f"\n🔍 Validating {name}...")
            try:
                result = validator()
                results.append(result)
            except Exception as e:
                self.errors.append(f"❌ Validation error in {name}: {e}")
                results.append(False)
        
        all_passed = all(results)
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 VALIDATION SUMMARY")
        print("=" * 70)
        
        if self.passed:
            print(f"\n✅ Passed Checks ({len(self.passed)}):")
            for check in self.passed:
                print(f"   {check}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   {warning}")
        
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"   {error}")
        
        print("\n" + "=" * 70)
        
        if all_passed and not self.errors:
            print("✅ ALL VALIDATIONS PASSED - Ready for production")
        else:
            print("❌ VALIDATION FAILED - Fix errors before deploying")
        
        print("=" * 70 + "\n")
        
        return all_passed, self.errors, self.warnings, self.passed


def main():
    """Run configuration validation."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Validate production environment configuration"
    )
    parser.add_argument(
        '--env-file',
        default='.env',
        help='Path to .env file (default: .env)'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as errors'
    )
    
    args = parser.parse_args()
    
    # Check if env file exists
    if not os.path.exists(args.env_file):
        print(f"❌ Environment file not found: {args.env_file}")
        sys.exit(1)
    
    # Run validation
    validator = ProductionConfigValidator(args.env_file)
    all_passed, errors, warnings, passed = validator.validate_all()
    
    # Exit with appropriate code
    if errors:
        sys.exit(1)
    elif warnings and args.strict:
        print("\n⚠️  Strict mode: Treating warnings as errors")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

