import datetime
from typing import Dict, List, Optional, Any

class TwinEngine:
    """
    Digital twin of the Historical Market Data PCAP Pipeline.
    Simulates state transitions, job creation, and event generation.
    """
    FEEDS = ["A-FEED", "B-FEED"]
    MESSAGE_CODES = [
        "FEED_A_CORE_L2_DC1", "FEED_A_CORE_L3_DC1",
        "FEED_B_CORE_L2_DC1", "FEED_B_CORE_L3_DC1"
    ]

    def __init__(self):
        self.jobs = {}          # job_id -> job dict
        self.pcap_files = {}    # (feed, code, date) -> file dict
        self.event_log = []     # accumulated events
        self.job_counter = 0
        self.holidays = set()   # date strings "YYYY-MM-DD"

    def _generate_job_id(self) -> str:
        self.job_counter += 1
        return f"job-{self.job_counter}"

    def _is_valid_date(self, date_str: str) -> bool:
        try:
            datetime.date.fromisoformat(date_str)
            return True
        except ValueError:
            return False

    def _is_weekday(self, date_str: str) -> bool:
        dt = datetime.date.fromisoformat(date_str)
        return dt.weekday() < 5

    def _is_holiday(self, date_str: str) -> bool:
        return date_str in self.holidays

    def _emit_event(self, events: List[Dict], event_type: str, payload: Any = None):
        event = {"type": event_type}
        if payload:
            event["payload"] = payload
        events.append(event)
        self.event_log.append(event)

    def _file_key(self, feed: str, code: str, date: str) -> tuple:
        return (feed, code, date)

    def _generate_filename(self, date_str: str) -> str:
        return f"LMEFTcad_{date_str.replace('-', '')}.zip"

    def _get_file_state_str(self, feed: str, code: str, date: str) -> str:
        key = self._file_key(feed, code, date)
        if key in self.pcap_files:
            return self.pcap_files[key]["state"]
        return "not_downloaded"

    # ----------------------------------------------------------------------
    # Public dispatch interface
    # ----------------------------------------------------------------------
    def dispatch(self, command: str, params: dict) -> dict:
        events = []
        state = ""
        error = None
        try:
            if command == "set_holidays":
                if "dates" not in params:
                    raise ValueError("missing_params: dates required")
                self.holidays = set(params["dates"])
                state = "holidays_set"
            elif command == "trigger_download":
                self._trigger_download(params, events)
                state = "download_triggered"
            elif command == "complete_download":
                self._complete_download(params, events)
                state = "download_completed"
            elif command == "trigger_validation":
                self._trigger_validation(params, events)
                state = "validation_triggered"
            elif command == "complete_validation":
                self._complete_validation(params, events)
                state = "validation_completed"
            elif command == "trigger_upload":
                self._trigger_upload(params, events)
                state = "upload_triggered"
            elif command == "complete_upload":
                self._complete_upload(params, events)
                state = "upload_completed"
            elif command == "trigger_archive":
                self._trigger_archive(params, events)
                state = "archive_triggered"
            elif command == "complete_archive":
                self._complete_archive(params, events)
                state = "archive_completed"
            elif command == "cron_download_task":
                self._cron_download(params, events)
                state = "cron_download_completed"
            elif command == "cron_validation_task":
                self._cron_validation(params, events)
                state = "cron_validation_completed"
            elif command == "cron_upload_task":
                self._cron_upload(params, events)
                state = "cron_upload_completed"
            elif command == "cron_archive_purge_task":
                self._cron_archive_purge(params, events)
                state = "cron_archive_completed"
            elif command == "get_file_state":
                feed = params.get("feedId")
                code = params.get("messageCode")
                date = params.get("businessDay")
                if not all([feed, code, date]):
                    raise ValueError("missing_params: feedId, messageCode, businessDay required")
                state = self._get_file_state_str(feed, code, date)
            else:
                error = "unknown_command"
        except ValueError as e:
            error = str(e)
        except Exception as e:
            error = f"unexpected_error: {str(e)}"
        result = {"events": events, "state": state}
        if error:
            result["error"] = error
        return result

    # ----------------------------------------------------------------------
    # Validation helpers
    # ----------------------------------------------------------------------
    def _check_valid_feed_code(self, feed: str, code: str):
        if feed not in self.FEEDS:
            raise ValueError(f"invalid_feed: {feed}")
        if code not in self.MESSAGE_CODES:
            raise ValueError(f"invalid_message_code: {code}")

    def _check_no_active_job(self, job_type: str, feed: str, code: str, date: str):
        for job in self.jobs.values():
            if (job["type"] == job_type
                    and job["params"]["feedId"] == feed
                    and job["params"]["messageCode"] == code
                    and job["params"]["businessDay"] == date
                    and job["state"] in ["triggered", "running"]):
                raise ValueError("job_already_active")

    def _create_job(self, job_type: str, feed: str, code: str, date: str, events: List[Dict]) -> str:
        self._check_no_active_job(job_type, feed, code, date)
        job_id = self._generate_job_id()
        job = {
            "job_id": job_id,
            "type": job_type,
            "params": {
                "feedId": feed,
                "messageCode": code,
                "businessDay": date
            },
            "state": "triggered",
            "error": None
        }
        self.jobs[job_id] = job
        self._emit_event(events, "JobTriggered", {
            "job_id": job_id,
            "type": job_type,
            "parameters": job["params"]
        })
        return job_id

    # ----------------------------------------------------------------------
    # Command implementations
    # ----------------------------------------------------------------------
    def _trigger_download(self, params: dict, events: List[Dict]):
        feed_id = params.get("feedId")
        if not feed_id:
            raise ValueError("missing_params: feedId required")
        business_day = params.get("businessDay")
        if not business_day:
            raise ValueError("missing_params: businessDay required")
        if not self._is_valid_date(business_day):
            raise ValueError("invalid_date_format")
        message_codes = params.get("messageCodes")
        if not message_codes:
            message_codes = self.MESSAGE_CODES
        for code in message_codes:
            self._check_valid_feed_code(feed_id, code)
            self._create_job("download", feed_id, code, business_day, events)

    def _complete_download(self, params: dict, events: List[Dict]):
        job_id = params.get("job_id")
        success = params.get("success")
        if job_id is None or success is None:
            raise ValueError("missing_params: job_id, success required")
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError("job_not_found")
        if job["type"] != "download":
            raise ValueError("invalid_job_type")
        if job["state"] not in ["triggered", "running"]:
            raise ValueError("invalid_job_state")
        if success:
            file_size = params.get("file_size", 0)
            job["state"] = "succeeded"
            self._emit_event(events, "JobSucceeded", {
                "job_id": job_id,
                "type": "download",
                "outputDescription": f"Downloaded {file_size} bytes"
            })
            feed = job["params"]["feedId"]
            code = job["params"]["messageCode"]
            date = job["params"]["businessDay"]
            key = self._file_key(feed, code, date)
            filename = self._generate_filename(date)
            if key in self.pcap_files:
                pcap = self.pcap_files[key]
                pcap["state"] = "downloaded"
                pcap["size"] = file_size
                pcap["filename"] = filename
            else:
                self.pcap_files[key] = {
                    "feed_id": feed,
                    "message_code": code,
                    "business_day": date,
                    "state": "downloaded",
                    "size": file_size,
                    "filename": filename,
                    "validation_result": None,
                    "market_state_events": None
                }
        else:
            job["state"] = "failed"
            job["error"] = "download_error"
            self._emit_event(events, "JobFailed", {
                "job_id": job_id,
                "type": "download",
                "error": "download error"
            })
            self._emit_event(events, "DownloadFailureAlert", {
                "recipients": "technical_team",
                "alert_type": "download_failure",
                "details": {"job_id": job_id}
            })

    def _trigger_validation(self, params: dict, events: List[Dict]):
        feed_id = params.get("feedId")
        if not feed_id:
            raise ValueError("missing_params: feedId required")
        business_day = params.get("businessDay")
        if not business_day:
            raise ValueError("missing_params: businessDay required")
        message_codes = params.get("messageCodes")
        if not message_codes:
            message_codes = self.MESSAGE_CODES
        for code in message_codes:
            self._check_valid_feed_code(feed_id, code)
            key = self._file_key(feed_id, code, business_day)
            if key not in self.pcap_files or self.pcap_files[key]["state"] != "downloaded":
                raise ValueError("pcap_not_downloaded")
        for code in message_codes:
            self._create_job("validate", feed_id, code, business_day, events)

    def _complete_validation(self, params: dict, events: List[Dict]):
        job_id = params.get("job_id")
        success = params.get("success")
        if job_id is None or success is None:
            raise ValueError("missing_params: job_id, success required")
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError("job_not_found")
        if job["type"] != "validate":
            raise ValueError("invalid_job_type")
        if job["state"] not in ["triggered", "running"]:
            raise ValueError("invalid_job_state")
        feed = job["params"]["feedId"]
        code = job["params"]["messageCode"]
        date = job["params"]["businessDay"]
        key = self._file_key(feed, code, date)
        pcap = self.pcap_files.get(key)
        if not pcap or pcap["state"] != "downloaded":
            raise ValueError("pcap_not_downloaded")
        if success:
            validation_result = params.get("validation_result")
            if not validation_result or "overall" not in validation_result:
                raise ValueError("missing_params: validation_result required")
            market_events = params.get("market_events", [])
            job["state"] = "succeeded"
            self._emit_event(events, "JobSucceeded", {
                "job_id": job_id,
                "type": "validate",
                "outputDescription": "Validation completed"
            })
            overall = validation_result["overall"]
            empty_file = validation_result.get("empty_file", "not_empty")
            pcap["validation_result"] = validation_result
            pcap["market_state_events"] = market_events
            if overall == "pass":
                pcap["state"] = "validated_pass"
            elif overall == "empty_normal":
                pcap["state"] = "empty_holiday"
            else:  # fail
                pcap["state"] = "validated_fail"
            if overall == "fail":
                self._emit_event(events, "ValidationFailureAlert", {
                    "recipients": "technical_team",
                    "alert_type": "validation_failure",
                    "details": {"feed": feed, "code": code, "date": date}
                })
            if empty_file == "exception_nonholiday":
                self._emit_event(events, "EmptyFileNonHolidayAlert", {
                    "recipients": "business_team",
                    "alert_type": "empty_nonholiday",
                    "details": {"feed": feed, "code": code, "date": date}
                })
            if market_events:
                self._emit_event(events, "MarketStateEventsRecorded", {
                    "feedId": feed,
                    "messageCode": code,
                    "businessDay": date,
                    "events": market_events
                })
            self._emit_dashboard_update(events, date)
        else:
            job["state"] = "failed"
            job["error"] = "validation_error"
            self._emit_event(events, "JobFailed", {
                "job_id": job_id,
                "type": "validate",
                "error": "validation error"
            })
            # Alert only if overall == fail (but no result available, so none)

    def _emit_dashboard_update(self, events: List[Dict], business_day: str):
        all_events = []
        for pcap in self.pcap_files.values():
            if pcap.get("business_day") == business_day and pcap.get("market_state_events"):
                all_events.extend(pcap["market_state_events"])
        self._emit_event(events, "DashboardUpdated", {
            "businessDay": business_day,
            "tradingStates": {"total_events": len(all_events), "events": all_events}
        })

    def _trigger_upload(self, params: dict, events: List[Dict]):
        feed_id = params.get("feedId")
        code = params.get("messageCode")
        date = params.get("businessDay")
        if not all([feed_id, code, date]):
            raise ValueError("missing_params: feedId, messageCode, businessDay required")
        self._check_valid_feed_code(feed_id, code)
        key = self._file_key(feed_id, code, date)
        if key not in self.pcap_files or self.pcap_files[key]["state"] != "validated_pass":
            raise ValueError("pcap_not_validated_pass")
        self._create_job("upload", feed_id, code, date, events)

    def _complete_upload(self, params: dict, events: List[Dict]):
        job_id = params.get("job_id")
        success = params.get("success")
        if job_id is None or success is None:
            raise ValueError("missing_params: job_id, success required")
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError("job_not_found")
        if job["type"] != "upload":
            raise ValueError("invalid_job_type")
        if job["state"] not in ["triggered", "running"]:
            raise ValueError("invalid_job_state")
        feed = job["params"]["feedId"]
        code = job["params"]["messageCode"]
        date = job["params"]["businessDay"]
        key = self._file_key(feed, code, date)
        pcap = self.pcap_files.get(key)
        if not pcap or pcap["state"] != "validated_pass":
            raise ValueError("pcap_not_validated_pass")
        if success:
            job["state"] = "succeeded"
            self._emit_event(events, "JobSucceeded", {
                "job_id": job_id,
                "type": "upload",
                "outputDescription": "Uploaded to distribution platform"
            })
            pcap["state"] = "uploaded"
        else:
            job["state"] = "failed"
            job["error"] = "upload_error"
            self._emit_event(events, "JobFailed", {
                "job_id": job_id,
                "type": "upload",
                "error": "upload error"
            })
            self._emit_event(events, "UploadFailureAlert", {
                "recipients": "technical_team",
                "alert_type": "upload_failure",
                "details": {"job_id": job_id}
            })

    def _trigger_archive(self, params: dict, events: List[Dict]):
        feed_id = params.get("feedId")
        code = params.get("messageCode")
        date = params.get("businessDay")
        if not all([feed_id, code, date]):
            raise ValueError("missing_params: feedId, messageCode, businessDay required")
        self._check_valid_feed_code(feed_id, code)
        key = self._file_key(feed_id, code, date)
        if key not in self.pcap_files or self.pcap_files[key]["state"] != "uploaded":
            raise ValueError("pcap_not_uploaded")
        self._create_job("archive", feed_id, code, date, events)

    def _complete_archive(self, params: dict, events: List[Dict]):
        job_id = params.get("job_id")
        success = params.get("success")
        if job_id is None or success is None:
            raise ValueError("missing_params: job_id, success required")
        job = self.jobs.get(job_id)
        if not job:
            raise ValueError("job_not_found")
        if job["type"] != "archive":
            raise ValueError("invalid_job_type")
        if job["state"] not in ["triggered", "running"]:
            raise ValueError("invalid_job_state")
        feed = job["params"]["feedId"]
        code = job["params"]["messageCode"]
        date = job["params"]["businessDay"]
        key = self._file_key(feed, code, date)
        pcap = self.pcap_files.get(key)
        if not pcap or pcap["state"] != "uploaded":
            raise ValueError("pcap_not_uploaded")
        if success:
            job["state"] = "succeeded"
            self._emit_event(events, "JobSucceeded", {
                "job_id": job_id,
                "type": "archive",
                "outputDescription": "Archived successfully"
            })
            pcap["state"] = "archived"
        else:
            job["state"] = "failed"
            job["error"] = "archive_error"
            self._emit_event(events, "JobFailed", {
                "job_id": job_id,
                "type": "archive",
                "error": "archive error"
            })
            self._emit_event(events, "OtherExceptionAlert", {
                "recipients": "technical_team",
                "alert_type": "other_exception",
                "details": {"job_id": job_id, "type": "archive", "error": "archive error"}
            })

    # ----------------------------------------------------------------------
    # Cron task implementations
    # ----------------------------------------------------------------------
    def _cron_download(self, params: dict, events: List[Dict]):
        business_day = params.get("businessDay")
        if not business_day:
            raise ValueError("missing_params: businessDay required")
        if not self._is_valid_date(business_day):
            raise ValueError("invalid_date_format")
        for feed in self.FEEDS:
            for code in self.MESSAGE_CODES:
                try:
                    self._create_job("download", feed, code, business_day, events)
                except ValueError:
                    # skip if job already active or other precondition issue
                    pass

    def _cron_validation(self, params: dict, events: List[Dict]):
        business_day = params.get("businessDay")
        if not business_day:
            raise ValueError("missing_params: businessDay required")
        # Collect all keys in "downloaded" state for this business day
        for key, pcap in list(self.pcap_files.items()):
            if pcap.get("business_day") == business_day and pcap["state"] == "downloaded":
                feed, code, date = key
                try:
                    self._create_job("validate", feed, code, date, events)
                except ValueError:
                    pass

    def _cron_upload(self, params: dict, events: List[Dict]):
        business_day = params.get("businessDay")
        if not business_day:
            raise ValueError("missing_params: businessDay required")
        for key, pcap in list(self.pcap_files.items()):
            if pcap.get("business_day") == business_day and pcap["state"] == "validated_pass":
                feed, code, date = key
                try:
                    self._create_job("upload", feed, code, date, events)
                except ValueError:
                    pass

    def _cron_archive_purge(self, params: dict, events: List[Dict]):
        # No businessDay required, process all "uploaded" files
        for key, pcap in list(self.pcap_files.items()):
            if pcap["state"] == "uploaded":
                feed, code, date = key
                try:
                    self._create_job("archive", feed, code, date, events)
                except ValueError:
                    pass