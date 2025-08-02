"""
Audio Processing Module with AWS Bedrock Integration
Handles audio transcription and intelligent project detail extraction
"""

import os
import json
import boto3
import time
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError
from pydub import AudioSegment
import tempfile
import uuid

class AudioProcessor:
    def __init__(self, aws_region='us-east-1', s3_bucket='homepro0723'):
        self.aws_region = aws_region
        self.s3_bucket = s3_bucket
        self.aws_available = False
        
        # Initialize logging
        import logging
        self.logger = logging.getLogger('AudioProcessor')
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        
        self.logger.info("🎵 Initializing AudioProcessor...")
        
        # Initialize AWS clients
        try:
            self.logger.info("🔑 Checking AWS credentials...")
            self.session = boto3.Session()
            credentials = self.session.get_credentials()
            
            if credentials is None:
                self.logger.warning("❌ No AWS credentials found")
                raise NoCredentialsError()
            
            self.logger.info("✅ AWS credentials found, testing access...")
            
            # Test credentials
            sts_client = boto3.client('sts')
            identity = sts_client.get_caller_identity()
            self.logger.info(f"✅ AWS credentials validated - Account: {identity.get('Account', 'Unknown')}")
            
            # Initialize clients
            self.s3_client = boto3.client('s3', region_name=self.aws_region)
            self.transcribe_client = boto3.client('transcribe', region_name=self.aws_region)
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=self.aws_region)
            
            self.aws_available = True
            self.logger.info("🚀 AWS Bedrock Audio Processor initialized successfully")
            self.logger.info(f"📍 Region: {self.aws_region}, S3 Bucket: {self.s3_bucket}")
            
        except Exception as e:
            self.logger.error(f"❌ AWS initialization failed: {e}")
            self.logger.warning("⚠️  Falling back to mock transcription mode")
            self.aws_available = False
            
        # Log available Bedrock models for debugging
        if self.aws_available:
            self._log_available_bedrock_models()
    
    def _log_available_bedrock_models(self):
        """Log available Bedrock models for debugging"""
        try:
            bedrock_client = boto3.client('bedrock', region_name=self.aws_region)
            response = bedrock_client.list_foundation_models()
            
            available_models = []
            for model in response.get('modelSummaries', []):
                model_id = model.get('modelId', '')
                model_name = model.get('modelName', '')
                provider = model.get('providerName', '')
                available_models.append(f"{provider}: {model_name} ({model_id})")
            
            if available_models:
                self.logger.info(f"🔍 Available Bedrock models ({len(available_models)}):")
                for model in available_models[:10]:  # Log first 10 models
                    self.logger.info(f"   • {model}")
                if len(available_models) > 10:
                    self.logger.info(f"   ... and {len(available_models) - 10} more models")
            else:
                self.logger.warning("⚠️  No Bedrock models found or accessible")
                
        except Exception as e:
            self.logger.warning(f"⚠️  Could not list Bedrock models: {e}")
    
    def convert_audio_format(self, input_path, output_format='wav'):
        """
        Convert audio file to supported format using pydub
        Supports: MP3, WAV, M4A, AAC, FLAC, OGG
        """
        try:
            # Load audio file
            audio = AudioSegment.from_file(input_path)
            
            # Create temporary output file
            temp_dir = tempfile.gettempdir()
            output_filename = f"converted_{uuid.uuid4().hex}.{output_format}"
            output_path = os.path.join(temp_dir, output_filename)
            
            # Convert to target format
            if output_format.lower() == 'wav':
                audio.export(output_path, format="wav")
            elif output_format.lower() == 'mp3':
                audio.export(output_path, format="mp3")
            else:
                # Default to WAV for transcription
                audio.export(output_path, format="wav")
            
            print(f"Audio converted from {input_path} to {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Audio conversion failed: {e}")
            return input_path  # Return original if conversion fails
    
    def upload_to_s3(self, file_path, s3_key=None):
        """Upload file to S3 and return the S3 URI"""
        if not self.aws_available:
            return None
        
        try:
            if s3_key is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = os.path.basename(file_path)
                s3_key = f"projects/audios/new/{timestamp}_{filename}"
            
            self.s3_client.upload_file(file_path, self.s3_bucket, s3_key)
            s3_uri = f"s3://{self.s3_bucket}/{s3_key}"
            print(f"File uploaded to S3: {s3_uri}")
            return s3_uri
            
        except Exception as e:
            print(f"S3 upload failed: {e}")
            return None
    
    def transcribe_audio(self, s3_uri, job_name=None, original_file_path=None):
        """
        Enhanced transcribe audio using AWS Transcribe with optimized settings
        """
        self.logger.info("🎤 Starting audio transcription...")
        
        if not self.aws_available:
            self.logger.warning("❌ AWS not available - using filename-based mock transcription")
            return self._mock_transcription(original_file_path)
        
        if not s3_uri:
            self.logger.warning("❌ No S3 URI provided - using filename-based mock transcription")
            return self._mock_transcription(original_file_path)
        
        self.logger.info(f"✅ Using AWS Transcribe for: {s3_uri}")
        
        try:
            if job_name is None:
                job_name = f"transcribe_job_{uuid.uuid4().hex}"
            
            # Enhanced transcription settings for home improvement projects
            transcribe_settings = {
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 3,  # Support up to 3 speakers
                'ShowAlternatives': True,
                'MaxAlternatives': 2,
                'VocabularyFilterMethod': 'remove',  # Remove profanity
                'ChannelIdentification': False
            }
            
            # Create custom vocabulary for home improvement terms
            custom_vocabulary = self._get_home_improvement_vocabulary()
            
            # Start transcription job with enhanced settings
            transcribe_params = {
                'TranscriptionJobName': job_name,
                'Media': {'MediaFileUri': s3_uri},
                'MediaFormat': self._detect_media_format(s3_uri),
                'LanguageCode': 'en-US',
                'Settings': transcribe_settings
            }
            
            # Add custom vocabulary if available
            if custom_vocabulary:
                transcribe_params['Settings']['VocabularyName'] = custom_vocabulary
            
            response = self.transcribe_client.start_transcription_job(**transcribe_params)
            
            self.logger.info(f"🚀 AWS Transcription job started: {job_name}")
            
            # Wait for completion
            max_wait_time = 300  # 5 minutes
            wait_interval = 10   # 10 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                status_response = self.transcribe_client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                
                status = status_response['TranscriptionJob']['TranscriptionJobStatus']
                
                if status == 'COMPLETED':
                    self.logger.info("✅ AWS Transcription completed successfully")
                    # Get transcript
                    transcript_uri = status_response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                    transcript_text = self._download_transcript(transcript_uri)
                    
                    # Clean up transcription job
                    try:
                        self.transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
                        self.logger.info("🧹 Transcription job cleaned up")
                    except:
                        pass  # Ignore cleanup errors
                    
                    self.logger.info(f"📝 Transcript length: {len(transcript_text)} characters")
                    return transcript_text
                    
                elif status == 'FAILED':
                    self.logger.error(f"❌ AWS Transcription job failed: {status_response}")
                    self.logger.warning("⚠️  Falling back to filename-based mock transcription")
                    return self._mock_transcription(original_file_path)
                
                time.sleep(wait_interval)
                elapsed_time += wait_interval
                if elapsed_time % 30 == 0:  # Log every 30 seconds
                    self.logger.info(f"⏳ Waiting for AWS transcription... ({elapsed_time}s/{max_wait_time}s)")
            
            self.logger.warning(f"⏰ AWS Transcription job timed out after {max_wait_time}s")
            self.logger.warning("⚠️  Falling back to filename-based mock transcription")
            return self._mock_transcription(original_file_path)
            
        except Exception as e:
            self.logger.error(f"❌ AWS Transcription failed: {e}")
            self.logger.warning("⚠️  Falling back to filename-based mock transcription")
            return self._mock_transcription(original_file_path)
    
    def _download_transcript(self, transcript_uri):
        """Download and parse transcript from S3"""
        try:
            import requests
            response = requests.get(transcript_uri)
            transcript_data = response.json()
            
            # Extract transcript text
            transcript_text = transcript_data['results']['transcripts'][0]['transcript']
            return transcript_text
            
        except Exception as e:
            print(f"Failed to download transcript: {e}")
            return self._mock_transcription(None)
    
    def _detect_media_format(self, s3_uri):
        """
        Detect media format from S3 URI
        """
        if s3_uri.lower().endswith('.mp3'):
            return 'mp3'
        elif s3_uri.lower().endswith('.mp4'):
            return 'mp4'
        elif s3_uri.lower().endswith('.flac'):
            return 'flac'
        elif s3_uri.lower().endswith('.ogg'):
            return 'ogg'
        else:
            return 'wav'  # Default to wav
    
    def _get_home_improvement_vocabulary(self):
        """
        Get or create custom vocabulary for home improvement terms
        Returns vocabulary name if available, None otherwise
        """
        try:
            # Check if vocabulary exists
            vocab_name = "home-improvement-vocab"
            
            # Try to get existing vocabulary
            try:
                response = self.transcribe_client.get_vocabulary(VocabularyName=vocab_name)
                if response['VocabularyState'] == 'READY':
                    return vocab_name
            except self.transcribe_client.exceptions.NotFoundException:
                # Vocabulary doesn't exist, create it
                home_improvement_terms = [
                    "bathroom", "kitchen", "renovation", "remodel", "plumbing",
                    "electrical", "HVAC", "flooring", "drywall", "painting",
                    "cabinets", "countertops", "backsplash", "fixtures", "appliances",
                    "contractor", "permit", "inspection", "demolition", "installation",
                    "tile", "hardwood", "laminate", "carpet", "vinyl",
                    "faucet", "toilet", "shower", "bathtub", "vanity",
                    "outlets", "switches", "lighting", "ceiling fan", "breaker",
                    "ductwork", "furnace", "air conditioning", "thermostat",
                    "insulation", "windows", "doors", "trim", "molding",
                    "budget", "timeline", "estimate", "quote", "materials"
                ]
                
                # Create vocabulary (this is async, so we'll return None for now)
                self.transcribe_client.create_vocabulary(
                    VocabularyName=vocab_name,
                    LanguageCode='en-US',
                    Phrases=home_improvement_terms
                )
                print(f"Created custom vocabulary: {vocab_name}")
                return None  # Vocabulary is being created, not ready yet
                
        except Exception as e:
            print(f"Error managing custom vocabulary: {e}")
            return None
    
    def _mock_transcription(self, file_path=None):
        """Return mock transcription for development/fallback"""
        self.logger.info("🎭 Using mock transcription (AWS not available)")
        
        # If we have a file path, try to extract meaningful information from it
        if file_path:
            filename = os.path.basename(file_path).lower()
            self.logger.info(f"📁 Analyzing filename for context: {filename}")
            
            # Try to infer project type from filename
            if any(word in filename for word in ['kitchen', 'cook']):
                self.logger.info("🍳 Detected kitchen project from filename")
                return "I need help with my kitchen project. Looking for renovation work including cabinets and countertops. Please provide a quote for the work needed."
            elif any(word in filename for word in ['bathroom', 'bath', 'shower']):
                self.logger.info("🚿 Detected bathroom project from filename")
                return "I need help with my bathroom project. Looking for renovation work including tiles and fixtures. Please provide a quote for the work needed."
            elif any(word in filename for word in ['plumb', 'pipe', 'leak']):
                self.logger.info("🔧 Detected plumbing project from filename")
                return "I have a plumbing issue that needs professional attention. Please help with repair work and provide a quote."
            elif any(word in filename for word in ['electric', 'wire', 'outlet']):
                self.logger.info("⚡ Detected electrical project from filename")
                return "I need electrical work done. Looking for professional electrical services. Please provide a quote for the work needed."
            elif any(word in filename for word in ['roof', 'gutter']):
                self.logger.info("🏠 Detected roofing project from filename")
                return "I need roofing work done. Looking for professional roofing services. Please provide a quote for the work needed."
            elif any(word in filename for word in ['floor', 'carpet', 'hardwood']):
                self.logger.info("🪵 Detected flooring project from filename")
                return "I need flooring work done. Looking for professional flooring installation or repair. Please provide a quote for the work needed."
            elif any(word in filename for word in ['paint']):
                self.logger.info("🎨 Detected painting project from filename")
                return "I need painting work done. Looking for professional painting services. Please provide a quote for the work needed."
            elif any(word in filename for word in ['hvac', 'heat', 'cool', 'air']):
                self.logger.info("🌡️ Detected HVAC project from filename")
                return "I need HVAC work done. Looking for heating and cooling system services. Please provide a quote for the work needed."
            else:
                self.logger.info("❓ No specific project type detected in filename")
        else:
            self.logger.info("❓ No filename provided for context analysis")
        
        # Generic fallback when no file context is available
        self.logger.info("🔄 Using generic fallback transcription")
        return "I need help with a home improvement project. Please provide professional services and a quote for the work needed."
    
    def extract_project_details_with_bedrock(self, transcript_text):
        """
        Enhanced AWS Bedrock integration for project detail extraction with multiple model fallbacks
        """
        if not self.aws_available:
            self.logger.warning("🚫 AWS not available - using fallback extraction")
            return self._extract_project_details_fallback(transcript_text)
        
        self.logger.info("🤖 Using AWS Bedrock for project detail extraction")
        
        # List of models to try in order of preference (newest and most capable first)
        models_to_try = [
            {
                "id": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                "name": "Claude 3.5 Sonnet v2",
                "type": "anthropic",
                "priority": "highest"
            },
            {
                "id": "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
                "name": "Claude 3.5 Sonnet",
                "type": "anthropic",
                "priority": "highest"
            },
            {
                "id": "anthropic.claude-3-sonnet-20240229-v1:0",
                "name": "Claude 3 Sonnet",
                "type": "anthropic",
                "priority": "high"
            },
            {
                "id": "anthropic.claude-3-haiku-20240307-v1:0", 
                "name": "Claude 3 Haiku",
                "type": "anthropic",
                "priority": "medium"
            },
            {
                "id": "anthropic.claude-v2:1",
                "name": "Claude v2.1",
                "type": "anthropic",
                "priority": "low"
            },
            {
                "id": "anthropic.claude-v2",
                "name": "Claude v2",
                "type": "anthropic",
                "priority": "low"
            },
            {
                "id": "amazon.titan-text-express-v1",
                "name": "Amazon Titan Text Express",
                "type": "amazon",
                "priority": "fallback"
            }
        ]
        
        access_denied_count = 0
        other_errors = []
        
        for model in models_to_try:
            try:
                self.logger.info(f"🔄 Trying model: {model['name']} ({model['id']})")
                result = self._try_bedrock_model(transcript_text, model)
                if result:
                    self.logger.info(f"✅ Successfully used model: {model['name']}")
                    return result
                    
            except Exception as e:
                error_msg = str(e)
                if "AccessDeniedException" in error_msg:
                    access_denied_count += 1
                    self.logger.warning(f"🔒 Model {model['name']} not enabled: Access denied")
                else:
                    other_errors.append(f"{model['name']}: {error_msg}")
                    self.logger.warning(f"❌ Model {model['name']} failed: {e}")
                continue
        
        # Provide helpful guidance based on error types
        if access_denied_count == len(models_to_try):
            self.logger.error("🚫 All Bedrock models are not enabled in your AWS account!")
            self.logger.error("📋 To enable Bedrock models:")
            self.logger.error("   1. Go to AWS Bedrock Console")
            self.logger.error("   2. Click 'Model access' in the sidebar")
            self.logger.error("   3. Enable 'Amazon Titan Text Express' (usually instant)")
            self.logger.error("   4. Optionally enable Claude models (may require approval)")
            self.logger.error("   5. See BEDROCK_SETUP_GUIDE.md for detailed instructions")
        elif access_denied_count > 0:
            self.logger.warning(f"🔒 {access_denied_count}/{len(models_to_try)} models not enabled")
            self.logger.warning("💡 Consider enabling more models for better performance")
        
        if other_errors:
            self.logger.warning(f"⚠️  Other errors encountered: {other_errors}")
        
        # If all models fail, use fallback
        self.logger.warning("🔄 All Bedrock models failed, falling back to intelligent text analysis")
        self.logger.info("✅ Fallback analysis will still provide structured project details")
        return self._extract_project_details_fallback(transcript_text)
    
    def _try_bedrock_model(self, transcript_text, model_config):
        """
        Try a specific Bedrock model for project detail extraction
        """
        # Enhanced prompt with confidence scoring and validation
        prompt = f"""
        You are an expert home improvement project analyst. Analyze this transcript and extract project details with high accuracy.

        Transcript: "{transcript_text}"

        Extract the following information and return as valid JSON:
        {{
            "title": "Brief descriptive title for the project",
            "project_type": "One of: Plumbing, Electrical, Kitchen, Bathroom, Roofing, Flooring, Painting, HVAC, General",
            "description": "Detailed description based on transcript",
            "budget_min": numeric_value_or_null,
            "budget_max": numeric_value_or_null,
            "timeline": "Timeline mentioned or null",
            "location": "Specific location mentioned or null",
            "urgency": "Low, Medium, or High",
            "key_requirements": ["list", "of", "key", "requirements"],
            "materials_mentioned": ["list", "of", "materials"],
            "contractor_type": "Type of contractor needed or null",
            "permits_needed": true_or_false,
            "complexity": "Simple, Medium, or Complex",
            "confidence": 0.0_to_1.0_confidence_score,
            "additional_notes": "Any additional relevant information"
        }}

        Guidelines:
        - Extract budget numbers carefully, looking for ranges or single amounts
        - Identify project type based on keywords and context
        - Set urgency based on language used (urgent, ASAP = High, flexible = Low)
        - Complexity: Simple = basic repairs, Complex = major renovations
        
        Return only valid JSON without any additional text or formatting.
        """
        
        if model_config["type"] == "anthropic":
            # Anthropic Claude models
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        elif model_config["type"] == "amazon":
            # Amazon Titan models
            body = json.dumps({
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 1000,
                    "temperature": 0.1,
                    "topP": 0.9
                }
            })
        else:
            raise ValueError(f"Unsupported model type: {model_config['type']}")
        
        response = self.bedrock_client.invoke_model(
            modelId=model_config["id"],
            body=body,
            contentType="application/json",
            accept="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        
        # Extract text based on model type
        if model_config["type"] == "anthropic":
            extracted_text = response_body['content'][0]['text']
        elif model_config["type"] == "amazon":
            extracted_text = response_body['results'][0]['outputText']
        else:
            raise ValueError(f"Unsupported model type for response parsing: {model_config['type']}")
        
        # Parse the JSON response
        try:
            # Clean the response text to extract JSON
            json_start = extracted_text.find('{')
            json_end = extracted_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_text = extracted_text[json_start:json_end]
            else:
                json_text = extracted_text
            
            project_details = json.loads(json_text)
            project_details['transcribed_text'] = transcript_text
            project_details['extraction_method'] = f'bedrock_{model_config["name"].lower().replace(" ", "_")}'
            
            self.logger.info(f"✅ Bedrock extraction successful - Project: {project_details.get('title', 'Unknown')}")
            self.logger.debug(f"📊 Bedrock extraction details: {project_details}")
            return project_details
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Failed to parse Bedrock JSON response: {e}")
            self.logger.debug(f"🔍 Raw Bedrock response: {extracted_text}")
            raise e
    
    def _extract_project_details_fallback(self, transcript_text):
        """Fallback extraction using simple text analysis"""
        self.logger.info("🔧 Using fallback text analysis for project extraction")
        import re
        
        text_lower = transcript_text.lower()
        
        # Extract project type
        project_types = {
            'plumbing': ['plumb', 'pipe', 'faucet', 'sink', 'toilet', 'drain', 'leak', 'water'],
            'electrical': ['electric', 'wire', 'outlet', 'switch', 'light', 'circuit', 'power'],
            'kitchen': ['kitchen', 'cabinet', 'countertop', 'appliance', 'stove', 'refrigerator'],
            'bathroom': ['bathroom', 'shower', 'bathtub', 'tile', 'vanity'],
            'roofing': ['roof', 'shingle', 'gutter'],
            'flooring': ['floor', 'carpet', 'hardwood', 'tile', 'laminate'],
            'painting': ['paint', 'wall', 'interior', 'exterior'],
            'hvac': ['heating', 'cooling', 'hvac', 'furnace', 'air conditioning']
        }
        
        detected_type = 'General'
        for project_type, keywords in project_types.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_type = project_type.title()
                break
        
        # Extract budget - optimized patterns to avoid partial matches
        budget_patterns = [
            # Range patterns first (most specific)
            r'(\d+)\s*to\s*(\d+)',                  # 15000 to 25000
            r'(\d{1,3}(?:,\d{3})*)\s*to\s*(\d{1,3}(?:,\d{3})*)',  # 15,000 to 25,000
            
            # Context-specific patterns (more specific)
            r'around\s*\$?(\d+)',                   # around $15000 or around 15000
            r'about\s*\$?(\d+)',                    # about $15000 or about 15000
            r'budget.*?\$?(\d+)',                   # budget is 15000
            
            # Dollar sign patterns
            r'\$(\d+(?:\.\d{2})?)',                 # $15000 or $15000.00
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $15,000 or $15000.00
            
            # Word-based patterns
            r'(\d+)\s*dollars?',                    # 15000 dollars
            r'(\d+)\s*bucks?',                      # 15000 bucks
        ]
        
        budget_numbers = []
        for pattern in budget_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:  # If we found matches with this pattern, process them and stop
                for match in matches:
                    if isinstance(match, tuple):
                        # Handle range patterns like "15000 to 25000"
                        for num in match:
                            if num:
                                try:
                                    value = int(num.replace(',', ''))
                                    if value > 100:  # Filter out small numbers
                                        budget_numbers.append(value)
                                except ValueError:
                                    continue
                    else:
                        try:
                            value = int(match.replace(',', ''))
                            if value > 100:  # Filter out small numbers
                                budget_numbers.append(value)
                        except ValueError:
                            continue
                break  # Stop after first successful pattern match
        
        # Remove duplicates and sort
        budget_numbers = sorted(list(set(budget_numbers)))
        
        budget_min = min(budget_numbers) if budget_numbers else None
        budget_max = max(budget_numbers) if len(budget_numbers) > 1 else None
        
        # Extract timeline - improved patterns
        timeline_patterns = {
            'asap': ['asap', 'urgent', 'immediately', 'right away', 'emergency'],
            'flexible': ['flexible', 'no rush', 'whenever', 'no hurry'],
            'specific_weeks': [r'(\d+)\s*weeks?', r'within\s*(\d+)\s*weeks?'],
            'specific_months': [r'(\d+)\s*months?', r'within\s*(\d+)\s*months?'],
            'specific_days': [r'(\d+)\s*days?', r'within\s*(\d+)\s*days?']
        }
        
        timeline = None
        
        # Check for specific timeframes first
        for time_type, patterns in timeline_patterns.items():
            if time_type.startswith('specific_'):
                unit = time_type.split('_')[1]
                for pattern in patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        number = match.group(1)
                        timeline = f"{number} {unit}"
                        break
                if timeline:
                    break
        
        # If no specific timeframe found, check for general keywords
        if not timeline:
            for timeline_type, keywords in timeline_patterns.items():
                if timeline_type.startswith('specific_'):
                    continue
                if any(keyword in text_lower for keyword in keywords):
                    timeline = timeline_type.upper() if timeline_type == 'asap' else timeline_type.title()
                    break
        
        if not timeline:
            timeline = None  # Leave blank if not specified
        
        # Extract location information
        location = None
        location_patterns = [
            r'in\s+the\s+(\w+)',  # "in the kitchen"
            r'(\w+)\s+renovation',  # "kitchen renovation"
            r'(\w+)\s+remodel',    # "bathroom remodel"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text_lower)
            if match:
                potential_location = match.group(1)
                if potential_location in ['kitchen', 'bathroom', 'bedroom', 'living', 'dining', 'basement', 'attic', 'garage']:
                    location = potential_location.title()
                    break
        
        # Extract key requirements
        key_requirements = []
        requirement_keywords = [
            'cabinet', 'countertop', 'appliance', 'tile', 'floor', 'paint', 'roof', 'plumbing', 
            'electrical', 'hvac', 'window', 'door', 'fixture', 'lighting'
        ]
        
        for keyword in requirement_keywords:
            if keyword in text_lower:
                key_requirements.append(keyword.title())
        
        return {
            'transcribed_text': transcript_text,
            'title': self._generate_title(transcript_text, detected_type),
            'project_type': detected_type,
            'description': transcript_text,
            'budget_min': budget_min,
            'budget_max': budget_max,
            'timeline': timeline,
            'location': location,
            'urgency': 'Medium',
            'key_requirements': key_requirements,
            'confidence': 0.6,  # Lower confidence for fallback method
            'extraction_method': 'fallback'
        }
    
    def _generate_title(self, text, project_type):
        """Generate a project title based on transcript content"""
        import re
        
        text_lower = text.lower()
        
        # Define title patterns based on project type and common phrases
        title_patterns = {
            'kitchen': [
                r'kitchen\s+(renovation|remodel|makeover|upgrade)',
                r'(renovate|remodel|upgrade)\s+.*kitchen',
                r'kitchen\s+(cabinet|countertop|appliance)',
            ],
            'bathroom': [
                r'bathroom\s+(renovation|remodel|makeover|upgrade)',
                r'(renovate|remodel|upgrade)\s+.*bathroom',
                r'bathroom\s+(tile|shower|vanity)',
            ],
            'plumbing': [
                r'plumbing\s+(emergency|repair|issue|problem)',
                r'(pipe|leak|drain|faucet)\s+(repair|replacement|fix)',
                r'water\s+(leak|damage|issue)',
            ],
            'electrical': [
                r'electrical\s+(work|repair|upgrade|installation)',
                r'(outlet|wiring|panel|circuit)\s+(installation|upgrade|repair)',
                r'electrical\s+(safety|code|inspection)',
            ],
            'roofing': [
                r'roof\s+(repair|replacement|maintenance)',
                r'(shingle|gutter|leak)\s+(repair|replacement)',
                r'storm\s+damage\s+repair',
            ],
            'flooring': [
                r'(hardwood|laminate|carpet|tile)\s+(installation|replacement)',
                r'floor\s+(installation|refinishing|repair)',
                r'flooring\s+(project|upgrade)',
            ],
            'painting': [
                r'paint\s+(interior|exterior|room|house)',
                r'painting\s+(project|job|service)',
                r'(wall|ceiling)\s+painting',
            ],
            'hvac': [
                r'(hvac|furnace|ac|air\s+conditioning)\s+(replacement|repair|installation)',
                r'heating\s+(system|repair|upgrade)',
                r'cooling\s+(system|repair|upgrade)',
            ]
        }
        
        # Try to find a specific pattern match
        project_key = project_type.lower()
        if project_key in title_patterns:
            for pattern in title_patterns[project_key]:
                match = re.search(pattern, text_lower)
                if match:
                    # Create title from the matched phrase
                    matched_text = match.group(0)
                    # Capitalize properly
                    title = ' '.join(word.capitalize() for word in matched_text.split())
                    return title
        
        # Fallback: try to extract key action words and create a descriptive title
        action_words = ['renovation', 'remodel', 'repair', 'installation', 'replacement', 'upgrade', 'makeover']
        location_words = ['kitchen', 'bathroom', 'bedroom', 'living room', 'basement', 'garage', 'deck']
        
        found_action = None
        found_location = None
        
        for action in action_words:
            if action in text_lower:
                found_action = action.capitalize()
                break
        
        for location in location_words:
            if location in text_lower:
                found_location = location.title()
                break
        
        # Create title based on what we found
        if found_location and found_action:
            return f"{found_location} {found_action}"
        elif found_location:
            return f"{found_location} {project_type} Project"
        elif found_action:
            return f"{project_type} {found_action}"
        
        # Final fallback: use first sentence if reasonable length
        sentences = text.split('.')
        if sentences:
            first_sentence = sentences[0].strip()
            if 10 <= len(first_sentence) <= 60:
                return first_sentence.capitalize()
        
        return f"{project_type} Project"
    
    def process_audio_file(self, file_path, progress_callback=None):
        """
        Enhanced main method to process audio file with progress tracking and optimization
        """
        try:
            print(f"Processing audio file: {file_path}")
            
            if progress_callback:
                progress_callback("Starting audio processing...", 0)
            
            # Step 1: Validate and convert audio format
            if progress_callback:
                progress_callback("Converting audio format...", 10)
            
            converted_path = self.convert_audio_format(file_path, 'wav')
            if not converted_path:
                return {"error": "Failed to convert audio format", "confidence": 0.0}
            
            # Step 2: Upload to S3 (can be done in parallel with other prep work)
            if progress_callback:
                progress_callback("Uploading to AWS S3...", 25)
            
            s3_uri = self.upload_to_s3(converted_path)
            if not s3_uri:
                return {"error": "Failed to upload to S3", "confidence": 0.0}
            
            # Step 3: Transcribe audio
            if progress_callback:
                progress_callback("Transcribing audio...", 40)
            
            transcript_text = self.transcribe_audio(s3_uri, original_file_path=file_path)
            if not transcript_text:
                return {"error": "Failed to transcribe audio", "confidence": 0.0}
            
            # Step 4: Extract project details using enhanced Bedrock
            if progress_callback:
                progress_callback("Analyzing project details...", 70)
            
            project_details = self.extract_project_details_with_bedrock(transcript_text)
            
            # Step 5: Validate and enhance results
            if progress_callback:
                progress_callback("Finalizing results...", 90)
            
            # Add transcription to results for transparency
            if isinstance(project_details, dict):
                project_details['transcript'] = transcript_text
                project_details['processing_status'] = 'success'
                
                # Add S3 information
                if s3_uri:
                    project_details['s3_uri'] = s3_uri
                    project_details['s3_key'] = s3_uri.replace(f"s3://{self.s3_bucket}/", "")
                
                # Validate confidence scores
                overall_confidence = project_details.get('confidence', 0.5)
                if overall_confidence < 0.3:
                    project_details['warning'] = 'Low confidence in extraction. Please review results.'
            
            # Step 6: Clean up temporary files
            self._cleanup_temp_files(converted_path, file_path)
            
            if progress_callback:
                progress_callback("Processing complete!", 100)
            
            return project_details
            
        except Exception as e:
            print(f"Audio processing failed: {e}")
            import traceback
            traceback.print_exc()
            
            error_result = {
                "error": f"Processing failed: {str(e)}", 
                "confidence": 0.0,
                "processing_status": 'failed'
            }
            
            # Clean up on error
            try:
                self._cleanup_temp_files(converted_path if 'converted_path' in locals() else None, file_path)
            except:
                pass
            
            return error_result
    
    def _cleanup_temp_files(self, converted_path, original_path):
        """
        Clean up temporary files safely
        """
        try:
            if converted_path and converted_path != original_path and os.path.exists(converted_path):
                os.remove(converted_path)
                print(f"Cleaned up temporary file: {converted_path}")
        except Exception as e:
            print(f"Warning: Could not clean up temporary file: {e}")
    
    def transcribe_audio_only(self, file_path, progress_callback=None):
        """
        Process audio file to get transcript only (no Bedrock analysis)
        """
        try:
            print(f"Transcribing audio file: {file_path}")
            
            if progress_callback:
                progress_callback("Starting audio transcription...", 0)
            
            # Step 1: Validate and convert audio format
            if progress_callback:
                progress_callback("Converting audio format...", 20)
            
            converted_path = self.convert_audio_format(file_path, 'wav')
            if not converted_path:
                return {"error": "Failed to convert audio format", "confidence": 0.0}
            
            # Step 2: Upload to S3
            if progress_callback:
                progress_callback("Uploading to AWS S3...", 40)
            
            s3_uri = self.upload_to_s3(converted_path)
            if not s3_uri:
                return {"error": "Failed to upload to S3", "confidence": 0.0}
            
            # Step 3: Transcribe audio
            if progress_callback:
                progress_callback("Transcribing audio...", 70)
            
            transcript_text = self.transcribe_audio(s3_uri, original_file_path=file_path)
            if not transcript_text:
                return {"error": "Failed to transcribe audio", "confidence": 0.0}
            
            # Step 4: Return transcript result
            if progress_callback:
                progress_callback("Transcription complete!", 100)
            
            result = {
                'transcript': transcript_text,
                'processing_status': 'transcription_complete',
                'confidence': 1.0,
                's3_uri': s3_uri,
                's3_key': s3_uri.replace(f"s3://{self.s3_bucket}/", "") if s3_uri else None
            }
            
            # Clean up temporary files
            self._cleanup_temp_files(converted_path, file_path)
            
            return result
            
        except Exception as e:
            print(f"Audio transcription failed: {e}")
            import traceback
            traceback.print_exc()
            
            error_result = {
                "error": f"Transcription failed: {str(e)}", 
                "confidence": 0.0,
                "processing_status": 'failed'
            }
            
            # Clean up on error
            try:
                self._cleanup_temp_files(converted_path if 'converted_path' in locals() else None, file_path)
            except:
                pass
            
            return error_result

    def get_processing_status(self, job_id=None):
        """
        Get status of processing job (for future async implementation)
        """
        # Placeholder for future async processing status
        return {"status": "completed", "progress": 100}