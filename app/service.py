#!/usr/bin/python
import json
import string
import asyncio
import random
import logging
from typing import Dict, List, Tuple, Optional, Any, Union

try:
    from ansible.module_utils import cyberark_client, robotic_helper, config
except (ImportError, ModuleNotFoundError):
    from module_utils import cyberark_client, robotic_helper, config

logger = logging.getLogger(__name__)


class CyberArkService:
    """Main service class for interacting with CyberArk API."""

    def __init__(self, cyberark_env: str, cert: str, key: str):
        """Initialize CyberArk service with environment and credentials.
        
        Args:
            cyberark_env: Environment name (e.g., 'STG', 'PRD')
            cert: Path to certificate file
            key: Path to private key file
        """
        self.cyberark_client = cyberark_client.CyberArkClient(
            env=cyberark_env, cert=cert, key=key
        )
        self.robotic_service = robotic_helper.RoboticHelper()
        logger.info("CyberArkService initialized for environment: %s", cyberark_env)

    async def get_account(
        self, zone: str, safename: str, username: str, address: str
    ) -> Dict[str, Any]:
        """Retrieve an account from CyberArk.
        
        Args:
            zone: The zone where the account is located
            safename: Name of the safe containing the account
            username: Username of the account
            address: Address associated with the account
            
        Returns:
            Dictionary containing account information
        """
        logger.debug(
            "Getting account: zone=%s, safe=%s, user=%s, address=%s",
            zone, safename, username, address
        )
        response = await self.cyberark_client.get_account(
            zone=zone, safename=safename, username=username, address=address
        )
        return {"found": True, "response": response}

    async def create_account(
        self,
        ecosystem: str,
        zone: str,
        address: str,
        env: str,
        port: str,
        database: str,
        techno: str,
        list_schemas: Optional[List[str]] = None,
        list_admin: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create one or more accounts in CyberArk.
        
        Args:
            ecosystem: The ecosystem name
            zone: The zone where accounts should be created
            address: Address associated with the accounts
            env: Environment (e.g., 'DEV', 'PROD')
            port: Port number
            database: Database name
            techno: Technology type
            list_schemas: List of schema names to create
            list_admin: List of admin accounts to create
            
        Returns:
            Dictionary with creation status and response details
        """
        list_account_to_create = self._build_list_account_to_create(
            ecosystem, address, database, port, techno, zone, env, list_schemas, list_admin
        )
        
        logger.info("Creating %d accounts in CyberArk", len(list_account_to_create))
        tasks = [
            asyncio.create_task(self.cyberark_client.create_account(**account))
            for account in list_account_to_create
        ]
        
        result = await asyncio.gather(*tasks, return_exceptions=True)
        success, list_response = self._format_create_account_result(result, list_account_to_create)
        
        if success:
            logger.info("Successfully created %d accounts", len(list_response))
            return {"created": True, "response": list_response}

        error_msg = f"Error creating accounts: {'-'.join(list_response)}"
        logger.error(error_msg)
        raise Exception(error_msg)

    async def delete_account(
        self,
        zone: str,
        safename: str,
        username: str,
        address: str,
        database: str
    ) -> Dict[str, Any]:
        """Delete an account from CyberArk.
        
        Args:
            zone: The zone where the account is located
            safename: Name of the safe containing the account
            username: Username of the account
            address: Address associated with the account
            database: Database name
            
        Returns:
            Dictionary with deletion status
        """
        logger.info(
            "Deleting account: zone=%s, safe=%s, user=%s, address=%s, db=%s",
            zone, safename, username, address, database
        )
        response = await self.cyberark_client.delete_account(
            zone=zone,
            safename=safename,
            username=username,
            address=address,
            database=database
        )
        return {"deleted": True, "response": response}

    async def get_password_or_create_account(
        self,
        ecosystem: str,
        zone: str,
        address: str,
        env: str,
        port: str,
        database: str,
        techno: str,
        list_schemas: Optional[List[str]] = None,
        list_admin: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get passwords or create accounts if they don't exist.
        
        Args:
            ecosystem: The ecosystem name
            zone: The zone where accounts should be created
            address: Address associated with the accounts
            env: Environment (e.g., 'DEV', 'PROD')
            port: Port number
            database: Database name
            techno: Technology type
            list_schemas: List of schema names to create
            list_admin: List of admin accounts to create
            
        Returns:
            Dictionary with operation status and account details
        """
        list_account_to_create = self._build_list_account_to_create(
            ecosystem, address, database, port, techno, zone, env, list_schemas, list_admin
        )
        password_created = False

        logger.info("Processing %d accounts (get or create)", len(list_account_to_create))
        
        for account in list_account_to_create:
            try:
                password = await self.cyberark_client.get_account(
                    account["zone"],
                    account["safename"],
                    account["user_name"],
                    account["address"],
                    account["database"]
                )
                if password:
                    account.update({"password": password})
                    logger.debug("Retrieved password for account: %s", account["user_name"])
                else:
                    await self.cyberark_client.create_account(**account)
                    password_created = True
                    logger.info("Created new account: %s", account["user_name"])
            except Exception as e:
                logger.error("Error processing account %s: %s", account["user_name"], str(e))
                raise

        return {"password_created": password_created, "accounts": list_account_to_create}

    @staticmethod
    def _generate_password(number: int = 1, techno: Optional[str] = None) -> str:
        """Generate a random password following security requirements.
        
        Args:
            number: Number of passwords to generate (default 1)
            techno: Technology type (for future password format customization)
            
        Returns:
            Generated password string
        """
        SYMBOLS = "!#%}"
        CHAR_LIST = string.ascii_lowercase + string.ascii_uppercase + string.digits + SYMBOLS

        pwd = []
        for _ in range(number):
            pwd = [
                random.choice(SYMBOLS),
                random.choice(SYMBOLS),
                random.choice(string.ascii_uppercase),
                random.choice(string.ascii_uppercase),
                random.choice(string.ascii_lowercase),
                random.choice(string.ascii_lowercase),
                random.choice(string.digits),
                random.choice(string.digits),
            ]
            for _ in range(17):
                pwd.append(random.choice(CHAR_LIST))
            random.shuffle(pwd)
        return "".join(pwd)

    @staticmethod
    def _get_reco_safe(techno: str, zone: str) -> str:
        """Get reconciliation safe name based on technology and zone.
        
        Args:
            techno: Technology type
            zone: Zone identifier
            
        Returns:
            Safe name for reconciliation accounts
        """
        if techno.lower() == "mongodb":
            return config.RECO_SAFE_TECHNO_MAPPING[techno.lower()][zone]
        return config.RECO_SAFE_TECHNO_MAPPING[techno.lower()]

    async def _is_safe_name_exist(self, safe_name: str, zone: str) -> bool:
        """Check if a safe exists in CyberArk.
        
        Args:
            safe_name: Name of the safe to check
            zone: Zone where the safe should exist
            
        Returns:
            True if safe exists, False otherwise
        """
        safe_detail = await self.cyberark_client.get_safe_detail(safe_name, zone)
        return safe_detail is not None

    def _get_list_client_safes(self, ecosystem: str, zone: str, env: str) -> Dict[str, str]:
        """Get the list of client safes for an ecosystem.
        
        Args:
            ecosystem: Ecosystem name
            zone: Zone identifier
            env: Environment (e.g., 'DEV', 'PROD')
            
        Returns:
            Dictionary with 'generic' and 'service' safe names
        """
        short_name_safe = self.robotic_service.build_short_name_safe(ecosystem=ecosystem, region=zone)
        safe_gen = f"{short_name_safe}--{config.ACCOUNT_ENVIRONMENT_MAPPING[env.upper()]['GEN']}"
        safe_service = f"{short_name_safe}--{config.ACCOUNT_ENVIRONMENT_MAPPING[env.upper()]['SERVICE']}"

        if asyncio.run(self._is_safe_name_exist(safe_service, zone=zone)):
            return {
                "generic": safe_gen,
                "service": safe_service,
            }
        return {
            "generic": safe_gen,
            "service": safe_gen,
        }

    @staticmethod
    def ecosystem_regex_username_uses(ecosystem: str) -> str:
        """Format ecosystem name for username generation.
        
        Args:
            ecosystem: Ecosystem name to format
            
        Returns:
            Formatted ecosystem name (max 8 chars, no special chars)
        """
        ecosystem_regex = ecosystem.replace("-", "").replace("_", "")
        return ecosystem_regex[:8] if len(ecosystem_regex) > 8 else ecosystem_regex

    def _build_list_account_to_create(
        self,
        ecosystem: str,
        address: str,
        database: str,
        port: str,
        techno: str,
        zone: str,
        env: str,
        list_schemas: Optional[List[str]] = None,
        list_admin: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Build the list of accounts to create in CyberArk.
        
        Args:
            ecosystem: Ecosystem name
            address: Address associated with accounts
            database: Database name
            port: Port number
            techno: Technology type
            zone: Zone identifier
            env: Environment
            list_schemas: Optional list of schemas
            list_admin: Optional list of admin accounts
            
        Returns:
            List of account dictionaries ready for creation
        """
        list_safe = self._get_list_client_safes(ecosystem, zone, env)
        list_accounts = self.build_specific_field_values_mandatory_accounts(
            ecosystem, database, address, techno, zone, env, list_safe
        )
        
        if list_schemas:
            list_schemas_accounts = self.build_specific_field_values_schema_accounts(
                list_schemas, list_safe["generic"], database, techno
            )
            list_accounts.extend(list_schemas_accounts)

        if list_admin:
            list_admin_accounts = self.build_specific_field_values_admin_accounts(
                list_admin, list_safe["service"], techno
            )
            list_accounts.extend(list_admin_accounts)

        for account in list_accounts:
            account.update({
                "zone": zone,
                "address": address,
                "env": env.upper(),
                "password": self._generate_password(),
                "env_letter": env[0].upper(),
                "port": port,
                "database": database,
            })

        return list_accounts

    @staticmethod
    def build_specific_field_values_schema_accounts(
        list_schemas: List[str],
        safe_name: str,
        database: str,
        techno: str
    ) -> List[Dict[str, str]]:
        """Build schema accounts configuration for creation.
        
        Args:
            list_schemas: List of schema names
            safe_name: Safe name where accounts will be created
            database: Database name
            techno: Technology type
            
        Returns:
            List of schema account configurations
        """
        return [
            {
                "safe_name": safe_name,
                "account_type": f"{techno.upper()}{config.ACCOUNT_TYPE_SUFFIX['service']}",
                "user_name": user_name,
                "role": config.SCHEMA_CONF[techno.upper()]["role"],
                "comment": f"{config.SCHEMA_CONF[techno.upper()]['comment']}{database}",
            } for user_name in list_schemas
        ]

    @staticmethod
    def build_specific_field_values_admin_accounts(
        list_admin: List[str],
        safe_name: str,
        techno: str
    ) -> List[Dict[str, str]]:
        """Build admin accounts configuration for creation.
        
        Args:
            list_admin: List of admin usernames
            safe_name: Safe name where accounts will be created
            techno: Technology type
            
        Returns:
            List of admin account configurations
        """
        return [
            {
                "safe_name": safe_name,
                "account_type": f"{techno.upper()}{config.ACCOUNT_TYPE_SUFFIX['service']}",
                "user_name": user_name,
                "role": config.ADMIN_CONF[techno.upper()]["role"],
                "comment": config.ADMIN_CONF[techno.upper()]['comment'],
            } for user_name in list_admin
        ]

    @staticmethod
    def build_specific_field_values_mandatory_accounts(
        ecosystem: str,
        database: str,
        address: str,
        techno: str,
        zone: str,
        env: str,
        list_safe: Dict[str, str]
    ) -> List[Dict[str, str]]:
        """Build mandatory accounts configuration for creation.
        
        Args:
            ecosystem: Ecosystem name
            database: Database name
            address: Address associated with accounts
            techno: Technology type
            zone: Zone identifier
            env: Environment
            list_safe: Dictionary with safe names
            
        Returns:
            List of mandatory account configurations
        """
        list_accounts = []
        for key, value in config.ACCOUNT_FUNC_CATEGORY_MAPPING.items():
            comment = value['comment']
            if key == "RECONCILE":
                saf_name = CyberArkService._get_reco_safe(techno, zone)
                user_name_string = f"{zone[-1]}CYBERARKRECO"
            else:
                short_appli = "" if key == "MONITORING" else CyberArkService.ecosystem_regex_username_uses(ecosystem)
                saf_name = list_safe[value["policy"]]
                user_name_string = (f"{zone[-1]}"
                                    f"{techno[0:2]}"
                                    f"{value['code']}"
                                    f"{short_appli}")
            
            user_name = (f"{config.USERNAME_PREFIX[value['policy']]}"
                         f"{user_name_string}"
                         f"{env[0].upper()}")

            list_accounts.append({
                "safe_name": saf_name,
                "account_type": f"{techno.upper()}{config.ACCOUNT_TYPE_SUFFIX['policy']}",
                "user_name": user_name,
                "role": value["role"],
                "comment": comment,
            })
        return list_accounts

    @staticmethod
    def _format_create_account_result(
        results: List[Any],
        list_account_to_create: List[Dict[str, Any]]
    ) -> Tuple[bool, Union[List[Dict[str, Any]], List[str]]]:
        """Format the results of account creation.
        
        Args:
            results: List of results from account creation
            list_account_to_create: Original list of accounts to create
            
        Returns:
            Tuple with success status and either list of created accounts or error messages
        """
        list_error_message = []
        account_created = []
        success = True
        
        for index, item in enumerate(results):
            account = list_account_to_create[index]
            password = account.pop("password")
            
            if isinstance(item, Exception):
                success = False
                list_error_message.append(f"Error creating account: {str(item)} - {account}")
            elif "ErrorMessage" in item.get("Content", {}):
                success = False
                list_error_message.append(
                    f"{item['Content']['ErrorMessage']}"
                    f"- status_code: {item.get('Response', {}).get('code', 'unknown')}"
                    f" : {account}"
                )
            else:
                list_error_message.append(f"{account}: created\n")
                try:
                    # Case 409, account already exists
                    account_info = item.get("Content", {}).get("value", [])[0]
                except (KeyError, IndexError, TypeError):
                    # Case 201, account created
                    account_info = item.get("Content", {})
                
                if account_info:
                    account_created.append({
                        **account_info,
                        "password": password
                    })

        return (success, account_created) if success else (success, list_error_message)
