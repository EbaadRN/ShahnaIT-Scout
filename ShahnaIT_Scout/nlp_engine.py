"""nlp_engine.py - deterministic, offline resume parser + JD matcher (replaces the Groq calls).
Public API: parse_resume(text), analyze_match(resume_text, jd_text), extract_skills(text).
Stateless: only immutable module-level tables and a cached spaCy model; every call is a pure function of its inputs."""
import difflib
import re
import unicodedata
from datetime import date
from functools import lru_cache
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
try:
    from rapidfuzz import process
    from rapidfuzz.distance import OSA
except ImportError:                                    # difflib keeps the engine working without rapidfuzz
    process = None
# ---- skills catalogue: Canonical|alias|alias, ...  (700+ tech / SAP / ERP / QA / data / security / business skills)
_SKILLS = """Python,Java,JavaScript|JS|ECMAScript|ES6,TypeScript|TS,C,C++|CPP,C#|CSharp|C Sharp,Go|Golang,Rust,Ruby,PHP,Swift,Kotlin,Scala,R,Perl,Dart,Objective-C|ObjC,MATLAB,Julia,Lua,Haskell,Elixir,Erlang,Clojure,F#|FSharp,Groovy,COBOL,Fortran,Pascal,Delphi,Assembly,VBA,VBScript,Visual Basic|VB.NET|VB6,PowerShell,Bash|Shell Scripting|Unix Shell,Awk,SQL,PL/SQL|PLSQL,T-SQL|TSQL,HTML|HTML5,CSS|CSS3,SASS|SCSS,XML,JSON,YAML,GraphQL,Solidity,ABAP,ABAP OO|Object Oriented ABAP,Verilog,VHDL,SystemVerilog,Prolog,Lisp,OCaml,CoffeeScript,WebAssembly|WASM,LaTeX,Regex|Regular Expressions,SAS,Stata,SPSS,Tcl,Racket,Ada
React|React.js|ReactJS|React JS,Angular|AngularJS|Angular.js,Vue.js|Vue|VueJS,Svelte,Next.js|NextJS,Nuxt.js|NuxtJS,Gatsby,Redux|Redux Toolkit,MobX,NgRx,jQuery,Bootstrap,Tailwind CSS|TailwindCSS|Tailwind,Material UI|MUI,Ant Design,Webpack,Vite,Babel,Storybook,Ember.js|EmberJS,Backbone.js|Backbone,Three.js,D3.js|D3,Chart.js,Highcharts,Electron,PWA|Progressive Web Apps,Web Components,Responsive Design,Styled Components,RxJS,Handlebars,Thymeleaf,Jinja2|Jinja,Lodash,Axios,Socket.IO|SocketIO,WebSockets|WebSocket,WebRTC,Micro Frontends,Cross Browser Compatibility
Node.js|NodeJS|Node,Express.js|ExpressJS|Express,NestJS|Nest.js,Koa,Fastify,Django|Django REST Framework|DRF,Flask,FastAPI,Pyramid,Celery,Spring|Spring Framework,Spring Boot|SpringBoot,Spring MVC,Spring Security,Spring Cloud,Spring Data,Hibernate,JPA,JDBC,MyBatis,Struts,JSF,Servlets,JSP,Maven,Gradle,Ant,ASP.NET|ASP.NET Core|ASPNET,.NET|.NET Core|DotNet,Entity Framework,LINQ,Blazor,WCF,WPF,WinForms,Xamarin,MAUI,Ruby on Rails|Rails|RoR,Sinatra,Laravel,Symfony,CodeIgniter,CakePHP,Yii,WordPress,Drupal,Joomla,Magento,Shopify,WooCommerce,Phoenix,Gin,Vert.x,Quarkus,Micronaut,Play Framework,Akka,Dropwizard,gRPC,REST|RESTful|REST API|REST APIs|RESTful API,SOAP,Microservices|Micro services,Web Services,OAuth|OAuth2,JWT,OpenID Connect|OIDC,SAML,SSO,Swagger|OpenAPI,RabbitMQ,ActiveMQ,ZeroMQ,NATS,MQTT,AMQP,JMS,Struts2,Servlet
Android|Android SDK|Android Development,iOS|iOS Development,React Native,Flutter,Ionic,Cordova|PhoneGap,SwiftUI,Jetpack Compose,UIKit,Xcode,Android Studio,Core Data,Retrofit,Firebase,Kotlin Multiplatform,NativeScript,Unity,Unreal Engine,ARKit,ARCore,TestFlight,Fastlane,Game Development,OpenGL,Vulkan,DirectX,Blender,Maya
MySQL,PostgreSQL|Postgres,SQL Server|MSSQL|Microsoft SQL Server|MS SQL,Oracle|Oracle Database|Oracle DB,MongoDB|Mongo,Redis,Cassandra,DynamoDB,Elasticsearch|Elastic Search,OpenSearch,Solr,Neo4j,CouchDB,Couchbase,MariaDB,SQLite,DB2,Teradata,Snowflake,BigQuery,Redshift,Hive,HBase,Impala,Presto|Trino,Athena,Cosmos DB,Firestore,Aurora,RDS,Memcached,InfluxDB,TimescaleDB,ClickHouse,Greenplum,Vertica,Sybase,Informix,ArangoDB,Database Design,Data Modeling|Data Modelling,Stored Procedures,Query Optimization,Database Administration|DBA,Replication,Sharding,NoSQL,RDBMS,OLAP,OLTP,Data Warehousing|Data Warehouse|DWH,Indexing,Database Migration
AWS|Amazon Web Services,Azure|Microsoft Azure,GCP|Google Cloud|Google Cloud Platform,IBM Cloud,Oracle Cloud|OCI,Alibaba Cloud,DigitalOcean,Heroku,Vercel,Netlify,Cloudflare,EC2,S3,AWS Lambda|Lambda,ECS,EKS,Fargate,CloudFormation,CloudWatch,CloudFront,Route 53,IAM,VPC,SNS,SQS,Kinesis,AWS Glue|Glue,EMR,SageMaker,API Gateway,Elastic Beanstalk,Azure DevOps|VSTS|TFS,Azure Functions,AKS,Azure Data Factory|ADF,Azure Synapse,Azure Databricks,Azure AD|Entra ID,App Engine,GKE,Cloud Run,Cloud Functions,Dataflow,Dataproc,Pub/Sub,Docker,Kubernetes|K8s,Helm,Istio,Terraform,Ansible,Puppet,Chef,SaltStack,Pulumi,Vagrant,Packer,Jenkins,GitLab CI|GitLab CI/CD,GitHub Actions,CircleCI,Travis CI,Bamboo,TeamCity,ArgoCD|Argo CD,Spinnaker,CI/CD|CI CD|Continuous Integration|Continuous Delivery|Continuous Deployment,DevOps,DevSecOps,SRE|Site Reliability Engineering,Infrastructure as Code|IaC,Prometheus,Grafana,Datadog,New Relic,Splunk,Dynatrace,AppDynamics,Nagios,Zabbix,ELK Stack|ELK,Logstash,Kibana,Fluentd,Jaeger,OpenTelemetry,PagerDuty,Nginx,Apache HTTP Server|Apache Web Server,Tomcat,JBoss|WildFly,WebLogic,WebSphere,IIS,HAProxy,Envoy,Consul,HashiCorp Vault,Nomad,OpenShift,Rancher,Docker Swarm,Podman,Linux|Unix,Ubuntu,CentOS,RHEL|Red Hat,Windows Server,Cron,Load Balancing,Auto Scaling,Serverless,Cloud Computing,Cloud Migration,Disaster Recovery,High Availability,Capacity Planning,Kustomize,Kong,Apigee,MuleSoft|Mule ESB,WSO2,TIBCO
Apache Spark|Spark|PySpark,Hadoop,HDFS,MapReduce,Kafka|Apache Kafka,Flink,Storm,Airflow|Apache Airflow,NiFi,Oozie,Sqoop,Flume,dbt,Databricks,Delta Lake,Iceberg,Hudi,Apache Beam,Luigi,Dagster,Prefect,ETL,ELT,Data Pipelines|Data Pipeline,Data Engineering,Data Integration,Data Migration,Data Governance,Data Quality,Master Data Management|MDM,Metadata Management,Data Lake,Data Mesh,Talend,Informatica PowerCenter|Informatica,SSIS,SSRS,SSAS,DataStage,Pentaho,Ab Initio,Fivetran,Matillion,Alteryx,Power BI|PowerBI,Tableau,QlikView,Qlik Sense|Qlik,Looker,Looker Studio|Data Studio,MicroStrategy,Cognos,SAP BusinessObjects|BusinessObjects|BOBJ,Domo,Superset,Metabase,Excel|Microsoft Excel|MS Excel,Advanced Excel,VLOOKUP,Pivot Tables,Power Query,DAX,Google Sheets,Data Analysis|Data Analytics,Data Visualization|Data Visualisation,Statistics|Statistical Analysis,A/B Testing,Predictive Modeling,Forecasting,Time Series,Pandas,NumPy,SciPy,Matplotlib,Seaborn,Plotly,Dash,Streamlit,Jupyter|Jupyter Notebook,Anaconda,Polars,Dask,Statsmodels,Hypothesis Testing,Regression Analysis,Business Intelligence|BI,Reporting,Big Data
Machine Learning|ML,Deep Learning|DL,Artificial Intelligence|AI,NLP|Natural Language Processing,Computer Vision,TensorFlow,Keras,PyTorch,scikit-learn|sklearn|Scikit Learn,XGBoost,LightGBM,CatBoost,Hugging Face|HuggingFace,Transformers,BERT,GPT,LLM|LLMs|Large Language Models,Generative AI|GenAI|Gen AI,LangChain,LlamaIndex,RAG|Retrieval Augmented Generation,Prompt Engineering,OpenAI|OpenAI API,ChatGPT,Llama,Mistral,Stable Diffusion,GANs,CNN,RNN,LSTM,Reinforcement Learning,Transfer Learning,Fine-tuning|Fine Tuning,Feature Engineering,Model Deployment,MLOps,MLflow,Kubeflow,Vertex AI,Azure ML,DVC,ONNX,TensorRT,OpenCV,YOLO,spaCy,NLTK,Gensim,Word2Vec,TF-IDF,Sentiment Analysis,Named Entity Recognition|NER,Text Classification,Topic Modeling,OCR|Tesseract,Speech Recognition,Recommendation Systems|Recommender Systems,Anomaly Detection,Clustering,Classification,Dimensionality Reduction|PCA,Random Forest,Gradient Boosting,SVM,Naive Bayes,Decision Trees,K-Means,Bayesian Methods,Ray,Pinecone,Milvus,Weaviate,FAISS,ChromaDB|Chroma,Qdrant,Vector Database,Embeddings,Semantic Search,AutoML,Explainable AI|XAI|SHAP,Data Science,Neural Networks,Robotics,ROS
Selenium,Cypress,Playwright,Puppeteer,Appium,TestNG,JUnit,Mockito,PyTest,Jest,Mocha,Chai,Jasmine,Karma,Cucumber,BDD,TDD,Robot Framework,SoapUI,JMeter,LoadRunner,Gatling,Locust,K6,Postman,REST Assured|RestAssured,Katalon,TestRail,Zephyr,UFT|QTP|Micro Focus UFT,Manual Testing,Automation Testing|Test Automation,Functional Testing,Regression Testing,Performance Testing,Load Testing,Smoke Testing,Sanity Testing,UAT|User Acceptance Testing,Integration Testing,Unit Testing,API Testing,Mobile Testing,Security Testing,Penetration Testing|Pen Testing|Pentesting,Test Planning,Test Cases,Test Strategy,Defect Tracking|Bug Tracking,Quality Assurance|QA,Quality Control|QC,ISTQB,BrowserStack,Sauce Labs,SonarQube,Test Data Management,System Integration Testing|SIT,End to End Testing|E2E Testing
Cybersecurity|Cyber Security|Information Security|InfoSec,Network Security,Application Security|AppSec,OWASP,Vulnerability Assessment,SIEM,QRadar,SOC,Incident Response,Threat Modeling,Ethical Hacking,Burp Suite,Metasploit,Nmap,Wireshark,Nessus,Kali Linux,Firewall|Firewalls,Palo Alto,Fortinet|FortiGate,Check Point,Cisco ASA,IDS/IPS,VPN,PKI,SSL/TLS|SSL|TLS,Encryption|Cryptography,Okta,CyberArk,Zero Trust,ISO 27001,SOC 2,GDPR,HIPAA,PCI DSS,NIST,CISSP,CEH,Compliance,Risk Management,Audit|Auditing,Identity and Access Management|IAM Policies,Endpoint Security,Data Loss Prevention|DLP
TCP/IP,DNS,DHCP,BGP,OSPF,MPLS,VLAN,LAN,WAN,Routing and Switching,Cisco,Juniper,CCNA,CCNP,CCIE,SD-WAN,F5,VMware|vSphere|ESXi,Hyper-V,Citrix,Virtualization,SAN,NAS,NetApp,Backup,Veeam,Commvault,Active Directory,LDAP,Exchange Server,Office 365|Microsoft 365|O365,SharePoint,Intune,SCCM|Configuration Manager,Group Policy,ITIL|ITIL v4,ITSM,ServiceNow,BMC Remedy|Remedy,Help Desk|Service Desk,Technical Support,Troubleshooting,Patch Management,Asset Management,Monitoring,System Administration|Server Administration|SysAdmin,Windows Administration,Linux Administration,Network Administration,Data Center,Embedded Systems,Embedded C,RTOS,FreeRTOS,Arduino,Raspberry Pi,STM32,Microcontrollers,PLC,SCADA,HMI,IoT,Zigbee,LoRa,Bluetooth,CAN Bus,I2C,SPI,UART,FPGA,PCB Design,Altium,AutoCAD,SolidWorks,CATIA,ANSYS,Revit,STAAD Pro,Simulink,LabVIEW,AUTOSAR,Yocto,Device Drivers,Linux Kernel,Firmware,5G,LTE,VoIP,SIP,Blockchain,Ethereum,Hyperledger,Smart Contracts,Web3
SAP,SAP ABAP,SAP HANA|HANA,SAP S/4HANA|S/4HANA|S4HANA|S/4 HANA|SAP S4 HANA|SAP S/4,SAP ECC|ECC,SAP FICO|FICO|SAP FI/CO,SAP FI|SAP Finance,SAP CO|SAP Controlling,SAP MM|SAP Materials Management,SAP SD|SAP Sales and Distribution,SAP PP|SAP Production Planning,SAP QM|SAP Quality Management,SAP PM|SAP Plant Maintenance,SAP WM|SAP Warehouse Management,SAP EWM|Extended Warehouse Management,SAP HCM|SAP HR|SAP HRMS,SAP SuccessFactors|SuccessFactors,SAP Ariba|Ariba,SAP BW|SAP BW/4HANA|BW/4HANA|SAP BI,SAP BODS|BODS|SAP Data Services,SAP Fiori|Fiori,SAPUI5|SAP UI5|UI5|OpenUI5,SAP CPI|SAP Cloud Platform Integration|SAP Integration Suite,SAP PI/PO|SAP PI|SAP PO|SAP XI|PI/PO,SAP BTP|SAP Business Technology Platform|SAP Cloud Platform,SAP CAP|Cloud Application Programming,SAP RAP|RESTful ABAP Programming,CDS Views|CDS|Core Data Services,AMDP,OData|SAP Gateway,SAP NetWeaver|NetWeaver,IDoc|IDocs,BAPI|BAPIs,BADI|BADIs,RFC,ALE,EDI,User Exits,Enhancement Framework|Enhancements,SmartForms,SAPscript,Adobe Forms,ALV,BDC,LSMW,Module Pool|Dialog Programming,SAP Workflow,SAP Solution Manager|SolMan,SAP GRC|GRC,SAP Basis|Basis,SAP Security,SAP CRM,SAP SRM,SAP SCM,SAP APO|APO,SAP IBP|IBP,SAP TM|SAP Transportation Management,SAP EHS,SAP PS|SAP Project System,SAP PLM,SAP IS-U|IS-U,SAP IS-Retail|IS Retail,SAP Concur|Concur,SAP C4C|Cloud for Customer,SAP Commerce|Hybris,SAP CPQ,SAP Analytics Cloud|SAC,SAP Lumira,SAP MDG|Master Data Governance,SAP GTS,SAP FSCM,SAP BPC|BPC,SAP BRF+|BRF+,SAP Business One|SAP B1,SAP Business ByDesign|ByDesign,SAP Activate,SAP Migration Cockpit|LTMC,SAP Data Migration,SAP Implementation,SAP Support,SAP AMS,SAP Upgrade,SAP Transport Management|TMS,SAP Signavio|Signavio,SAP Datasphere,SAP Build,Order to Cash|O2C|OTC,Procure to Pay|P2P,Record to Report|R2R,Hire to Retire,Accounts Payable,Accounts Receivable,General Ledger,Asset Accounting,Month End Close|Month-End Closing,Cost Center Accounting,Profit Center Accounting,Product Costing,Material Ledger,Credit Management,Inventory Management,Procurement|Purchasing,Vendor Management,Demand Planning,MRP,Variant Configuration,Batch Management,Subcontracting,Stock Transfer,Intercompany
Salesforce|SFDC,Apex,Lightning Web Components|LWC,Aura Components|Aura,Visualforce,SOQL,SOSL,Flow Builder|Salesforce Flows,Sales Cloud,Service Cloud,Marketing Cloud,Experience Cloud|Community Cloud,Salesforce CPQ,Pardot|Account Engagement,Salesforce Admin,Salesforce DX|SFDX,Dynamics 365|MS Dynamics|Dynamics CRM|D365,Dynamics AX,Dynamics NAV|Navision,Business Central,Power Apps|PowerApps,Power Automate|MS Flow,Power Platform,Oracle EBS|Oracle E-Business Suite,Oracle Fusion|Fusion Applications,Oracle Cloud ERP,Oracle HCM,Oracle SCM,Oracle Forms,Oracle Reports,Oracle APEX,OBIEE|OAC,Oracle SOA|SOA Suite,Oracle ADF,PeopleSoft,JD Edwards|JDE,Siebel,Hyperion,Oracle EPM,NetSuite,Workday|Workday HCM,Workday Financials,Infor,Epicor,Sage,QuickBooks,Zoho,HubSpot,Odoo,Tally|Tally ERP|Tally Prime,Microsoft Project|MS Project,Mainframe,JCL,CICS,VSAM,RPA,UiPath,Automation Anywhere,Blue Prism,HL7,FHIR,Epic,Cerner,Murex,Bloomberg,SWIFT,Temenos,Finacle,Flexcube,Calypso
Git,GitHub,GitLab,Bitbucket,SVN|Subversion,Mercurial,Perforce,Jira,Confluence,Trello,Asana,Slack,Microsoft Teams|MS Teams,Zoom,Notion,Figma,Sketch,Adobe XD,InVision,Zeplin,Photoshop|Adobe Photoshop,Illustrator,After Effects,Premiere Pro,InDesign,Canva,Balsamiq,Axure,Miro,Lucidchart,Visio|MS Visio,UML,BPMN,IntelliJ|IntelliJ IDEA,Eclipse,Visual Studio|VS Code|Visual Studio Code,PyCharm,Vim,Zendesk,Freshdesk,Google Analytics,Google Tag Manager|GTM,Adobe Analytics,Mixpanel,Amplitude,UI Design,UX Design|UI/UX|UX,Wireframing,Prototyping,User Research,Usability Testing,Interaction Design,Design Systems,Visual Design,Motion Graphics,Video Editing
Agile,Scrum,Kanban,SAFe|Scaled Agile,Waterfall,Lean,Six Sigma|Lean Six Sigma,XP|Extreme Programming,Design Thinking,PMP,PRINCE2,CSM|Certified Scrum Master,CSPO,PMI-ACP,COBIT,TOGAF,CMMI,Sprint Planning,Backlog Grooming|Backlog Refinement,Retrospectives,User Stories,Product Backlog,Product Roadmap|Roadmapping,OKRs,KPIs|KPI,Domain-Driven Design|DDD,Clean Architecture,SOLID,Design Patterns,Object Oriented Programming|OOP|OOPS|OOAD|Object Oriented Design,Functional Programming,Data Structures,Algorithms|DSA|Data Structures and Algorithms,System Design|Solution Architecture|Software Architecture,Event-Driven Architecture|EDA,CQRS,Event Sourcing,Multithreading|Concurrency,Distributed Systems,Scalability,Performance Tuning|Performance Optimization,Code Review,Technical Documentation,SDLC|Software Development Life Cycle,Version Control,Debugging,API Design|API Development,Integration,Middleware,Enterprise Architecture
Project Management,Program Management,Product Management,Stakeholder Management,Business Analysis|Business Analyst,Requirement Gathering|Requirements Gathering|Requirements Analysis,Functional Specifications|FSD,BRD,Process Mapping,Process Improvement,Gap Analysis,Change Management,Budgeting,Financial Analysis,Financial Reporting,Financial Modeling,Accounting,Bookkeeping,Taxation,GST,TDS,IFRS,GAAP,Treasury,Payroll|Payroll Processing,Recruitment|Talent Acquisition|Recruiting,Sourcing|Candidate Sourcing,Boolean Search,Onboarding,Employee Engagement,HRIS,Performance Management,Compensation and Benefits|C&B,Training and Development|L&D,Employee Relations,HR Operations|HR Ops,Workforce Planning,Applicant Tracking System|ATS,Headhunting,Resume Screening,Negotiation,Client Management|Client Handling,Account Management,Sales,B2B Sales,Business Development,Lead Generation,CRM,Pre-Sales|Presales,Digital Marketing,SEO,SEM,PPC,Google Ads|AdWords,Social Media Marketing|SMM,Content Marketing,Email Marketing,Copywriting,Content Writing,Brand Management,Market Research,Competitive Analysis,Supply Chain|Supply Chain Management|SCM,Logistics,Inventory Control,Warehouse Management,Operations Management,Customer Service|Customer Support,Customer Success,Team Leadership|Team Management|People Management,Leadership,Strategic Planning,Mentoring|Coaching,Presentation Skills,Vendor Negotiation""".replace("\n", ",")
_IMPLIES = {k: v.split(",") for k, v in (x.split(">") for x in ("Spring Boot>Spring,Java;Spring>Java;Hibernate>Java;JPA>Java;React>JavaScript;Angular>JavaScript,TypeScript;Vue.js>JavaScript;"
            "Node.js>JavaScript;Next.js>React,JavaScript;Django>Python;Flask>Python;FastAPI>Python;Pandas>Python;NumPy>Python;PySpark>Python,Apache Spark;PyTorch>Python,Machine Learning;"
            "TensorFlow>Python,Machine Learning;SAP ABAP>ABAP,SAP;SAP HANA>SAP;SAP MM>SAP;SAP SD>SAP;SAP FICO>SAP;PostgreSQL>SQL;MySQL>SQL;SQL Server>SQL;Oracle>SQL;EKS>Kubernetes,AWS;"
            "Kubernetes>Docker;EC2>AWS;S3>AWS;AWS Lambda>AWS;Scrum>Agile;Kanban>Agile").split(";"))}
_AMBIG = set("c r go swift rust spring express spark chef puppet gin unity lean ray dash sage epic basis ecc apo ibp sac rpa sit soc lan wan xp bi ai dl ml qa qc ux ant storm tms ale rfc edi "
             "alv bdc cds flink ats crm seo sem ppc gst tds sales reporting monitoring backup integration classification clustering embeddings transformers algorithms enhancements "
             "leadership sage mdm san nas sip lte dns vpn".split())
def _k(s):
    """Normalisation key: 'React.js' == 'ReactJS' == 'react js'; keeps + and # so C++/C# survive; '.NET' -> 'dotnet'."""
    return re.sub(r"[^a-z0-9+#]", "", re.sub(r"^\.", "dot", s.strip().lower()))
def _build():
    alias, canon = {}, []
    for chunk in _SKILLS.split(","):
        names = [n.strip() for n in chunk.split("|") if n.strip()]
        canon += names[:1]
        for n in names:
            alias.setdefault(_k(n), names[0])
    return alias, canon, [k for k in alias if len(k) >= 5 and k.isalpha() or len(k) >= 8]
_ALIAS, _CANON, _FUZZY_KEYS = _build()
_NAME_STOP = set("resume curriculum vitae cv profile summary objective contact address email phone page career personal details information technical skills experience education work history "
                 "professional declaration references having around over about years year yrs months total overall with seeking looking worked working currently possess strong good excellent hands".split())
@lru_cache(maxsize=1)
def _nlp():
    try:
        import spacy
        return spacy.load("en_core_web_sm", disable=["lemmatizer"])
    except Exception:                                  # model missing -> regex-only mode, still functional
        return None
def _doc(text):
    nlp = _nlp()
    return None if nlp is None else nlp(text[:100000])
def _clean(text):
    t = unicodedata.normalize("NFKC", text or "")
    t = re.sub(r"[​-‏­﻿⁠]", "", t).replace("\r\n", "\n").replace("\r", "\n").replace("\x0c", "\n").replace("\t", "  ")
    t = re.sub(r"[●■□▪◦○➢➤✓✔►\uf0b7\uf0a7\uf0d8\uf076\uf0fc]", "•", re.sub(r"(?<=\w)-\n(?=[a-z])", "", t))      # unify bullets, de-hyphenate PDF line wraps
    return re.sub(r"[  ]+\n", "\n", re.sub(r"\n{3,}", "\n\n", re.sub(r"[  ]{2,}", "  ", t))).strip()
# ---------------------------------------------------------------- skills: exact n-grams + spaCy-guided fuzzy (Damerau-Levenshtein)
def _fuzzy(cand, listed=False):
    k = _k(cand)
    if len(k) < (5 if listed else 6) or k in _ALIAS or not k[0].isalpha():
        return None
    maxd = 1 if len(k) < 10 else 2
    if process is not None:
        hit = process.extractOne(k, _FUZZY_KEYS, scorer=OSA.distance, score_cutoff=maxd)
        hit = hit[0] if hit else None
    else:
        hit = (difflib.get_close_matches(k, _FUZZY_KEYS, n=1, cutoff=1 - maxd / len(k)) or [None])[0]
    return _ALIAS[hit] if hit and hit[0] == k[0] and abs(len(hit) - len(k)) <= maxd and (listed or len(hit) > 5) else None
def _listy(text, s, e):
    pre, post = text[max(0, s - 12):s].rstrip(" ")[-1:], text[e:e + 12].lstrip(" ")[:1]
    return (pre == "" or pre in ",;|•·:(\n/") and (post == "" or post in ",;|•·)\n/")
def extract_skills(text, use_nlp=True, with_counts=False):
    """Canonical skills found in text, ordered by (frequency desc, first appearance). Ambiguous words (Go, R, Spring...) only count inside lists."""
    text = _clean(text)
    found, first, seq = {}, {}, []
    for m in re.finditer(r"\.?[A-Za-z0-9][A-Za-z0-9+#.\-/&']*", text):
        w = m.group().rstrip(".-'/&")
        seq.append((w, m.start(), m.end()))
        if "/" in w or "&" in w:                       # 'HTML/CSS' also yields HTML and CSS
            seq += [(p, m.start(), m.end()) for p in re.split(r"[/&]", w) if p]
    i = 0
    while i < len(seq):
        for n in (4, 3, 2, 1):
            key = _k("".join(w for w, _, _ in seq[i:i + n])) if i + n <= len(seq) else ""
            if key in _ALIAS:
                s, e = seq[i][1], seq[i + n - 1][2]
                if (key in _AMBIG or len(key) < 2) and not _listy(text, s, e):
                    continue
                c = _ALIAS[key]
                found[c], first[c] = found.get(c, 0) + 1, first.get(c, s)
                i += n - 1
                break
        i += 1
    if use_nlp:                                        # context pass: noun chunks, PRODUCT/ORG entities and list items -> typo-tolerant match
        listed = {x.strip() for ln in text.split("\n") if len(re.findall(r"[,;|•·/]", ln)) >= 2 for x in re.split(r"[,;|•·/]", ln)}
        doc, cands = _doc(text), set(listed)
        if doc is not None:
            cands |= {c.text for c in doc.noun_chunks} | {e.text for e in doc.ents if e.label_ in ("PRODUCT", "ORG", "WORK_OF_ART", "LANGUAGE")}
        for c in sorted(cands)[:700]:
            c0 = c.strip()
            c = re.sub(r"(?i)^(?:the|a|an|my|our|strong|good|hands-on|working|knowledge of)\s+", "", c0)
            hit = _fuzzy(c, c0 in listed) if 5 <= len(c) <= 40 and len(c.split()) <= 4 and not re.search(r"\d{3}", c) else None
            if hit:
                found[hit], first[hit] = found.get(hit, 0) + 1, first.get(hit, max(0, text.lower().find(c.lower())))
    ranked = sorted(found, key=lambda c: (-found[c], first[c]))
    return (ranked, found) if with_counts else ranked
# ---------------------------------------------------------------- sections, dates, contact details
_HEADS = {"experience": "experience workexperience professionalexperience employmenthistory workhistory careerhistory employment relevantexperience experiencesummary",
          "education": "education educationalqualification educationalqualifications academicqualification academicqualifications academics academicbackground qualifications educationaldetails",
          "skills": "skills technicalskills keyskills coreskills corecompetencies technicalexpertise skillset technicalproficiency areasofexpertise itskills technologies toolsandtechnologies",
          "projects": "projects academicprojects keyprojects projectdetails projectexperience personalprojects",
          "certs": "certifications certification certificates licensesandcertifications trainingandcertifications courses",
          "summary": "summary professionalsummary profile careerobjective objective aboutme profilesummary executivesummary careersummary",
          "other": "personaldetails declaration languages interests hobbies references achievements awards personalinformation strengths contact contactdetails"}
_HEAD_MAP = {w: sec for sec, ws in _HEADS.items() for w in ws.split()}
def _sections(text):
    secs, cur = {"header": []}, "header"
    for ln in text.split("\n"):
        s = ln.strip(" :-–—•*#_|")
        m = re.match(r"^([A-Za-z &/]{3,32})\s*[:\-–]\s*(\S.*)$", s)
        name = _HEAD_MAP.get(re.sub(r"[^a-z]", "", (m.group(1) if m else s).lower())) if m or (0 < len(s) <= 40 and not re.search(r"[\d@]", s)) else None
        if name:
            cur = name
            secs.setdefault(cur, [])
            secs[cur] += [m.group(2)] if m else []
        else:
            secs.setdefault(cur, []).append(ln)
    return {k: "\n".join(v).strip() for k, v in secs.items()}
_MON = "jan feb mar apr may jun jul aug sep oct nov dec".split()
_M = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_D = rf"(?:{_M}\.?[\s,'’\-]*(?:(?:19|20)\d{{2}}|\d{{2}}(?!\d))|\d{{1,2}}[/.\-](?:19|20)\d{{2}}|(?:19|20)\d{{2}})"
_NOW = r"(?:Present|Current|Till\s*Date|Till\s*Now|Now|Ongoing|Today|Date)"
_RANGE = re.compile(rf"({_D})\s*(?:-|–|—|to|till|until|through)\s*({_D}|{_NOW})\b", re.I)
def _mi(s, today):
    """'Mar 2019' / '03/2019' / '2019' / 'Present' -> month index (year*12+month)."""
    s, cap = s.strip().lower(), today.year * 12 + today.month - 1
    if re.match(_NOW, s, re.I):
        return cap
    m = re.search(rf"({'|'.join(_MON)})[a-z]*\.?[\s,'’\-]*(\d{{4}}|\d{{2}})\b", s) or re.search(r"(\d{1,2})[/.\-]((?:19|20)\d{2})", s)
    if m:
        mo, y = (_MON.index(m.group(1)) if m.group(1).isalpha() else int(m.group(1)) - 1), int(m.group(2))
    else:
        mo, y = 5, int(re.search(r"(?:19|20)\d{2}", s).group())       # year-only: mid-year at both ends
    y += (2000 if y <= 50 else 1900) if y < 100 else 0
    return min(y * 12 + max(0, min(11, mo)), cap)
def _fmt(mi):
    return f"{_MON[mi % 12].title()} {mi // 12}"
def _ranges(text, today):
    out = []
    for m in _RANGE.finditer(text):
        try:
            a, b = _mi(m.group(1), today), _mi(m.group(2), today)
        except (AttributeError, ValueError):
            continue
        if 0 <= b - a <= 600 and a >= 1970 * 12:
            out.append((a, b, m))
    return out
def _union(iv):
    tot, last = 0, 0
    for a, b in sorted(iv):                            # overlapping jobs are counted once
        tot += max(0, b - max(a, last))
        last = max(last, b)
    return tot
_TLD = "com org net edu gov info biz dev tech co in io ai us uk ca au de ae sg me".split()
_ROLE = re.compile(r"\b(engineer|developer|consultant|architect|analyst|manager|lead|administrator|tester|designer|specialist|executive|associate|intern|director|head|scientist|recruiter|officer|coordinator|programmer|technician|accountant|trainee|expert|owner|president)\b", re.I)
_COMP = re.compile(r"\b(pvt|private|ltd|limited|inc|llc|llp|corp|corporation|technologies|technology|solutions|systems|services|consulting|software|infotech|labs|bank|group|industries|enterprises|global|softech|tech|infra|networks|digital)\b", re.I)
_CITIES = ("Bangalore,Bengaluru,Hyderabad,Secunderabad,Pune,Chennai,Mumbai,Navi Mumbai,Thane,New Delhi,Delhi,Noida,Greater Noida,Gurgaon,Gurugram,Ghaziabad,Faridabad,Kolkata,Ahmedabad,Surat,Vadodara,Jaipur,Lucknow,"
           "Kanpur,Nagpur,Indore,Bhopal,Patna,Ranchi,Bhubaneswar,Visakhapatnam,Vizag,Vijayawada,Guntur,Tirupati,Warangal,Coimbatore,Madurai,Trichy,Kochi,Cochin,Trivandrum,Thiruvananthapuram,Mysore,Mysuru,Mangalore,"
           "Hubli,Chandigarh,Mohali,Ludhiana,Amritsar,Dehradun,Goa,Raipur,Guwahati,Nashik,Aurangabad,London,Manchester,Dublin,New York,San Francisco,Seattle,Austin,Chicago,Boston,Dallas,Houston,Atlanta,Toronto,"
           "Vancouver,Sydney,Melbourne,Singapore,Dubai,Abu Dhabi,Doha,Riyadh,Kuala Lumpur,Berlin,Munich,Amsterdam,Paris,Zurich,Tokyo").split(",")
_CITY_RE = re.compile(r"\b(" + "|".join(sorted(_CITIES, key=len, reverse=True)) + r")\b(?:\s*,\s*(Karnataka|Telangana|Maharashtra|Tamil Nadu|Andhra Pradesh|Kerala|Delhi|NCR|Haryana|Uttar Pradesh|Gujarat|"
                      r"West Bengal|Rajasthan|Madhya Pradesh|Punjab|Odisha|India|USA|UK|UAE|Canada|Australia|Germany|Singapore|Ireland))?")
_cl = lambda x: re.sub(r"^[^\w(]+|[\s,;|:\-–]+$", "", re.sub(r"(?i)[\s,;|]*\b(?:from|since|till|until|during|between)\s*$", "", x or "")).strip()
def _email(text):
    t = re.sub(r"(?i)\s*[\[(]at[\])]\s*", "@", re.sub(r"(?i)\s*[\[(]dot[\])]\s*", ".", text)).replace("mailto:", " ")
    for m in re.finditer(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}", t):         # aggressive fallback pattern from the spec
        local, dom = m.group().strip(".-_").replace("|", "").rsplit("@", 1)
        labels = dom.split(".")
        last = labels[-1].lower()
        if last not in _TLD and len(last) > 3:                                           # 'x.comPhone' -> 'x.com'
            labels[-1] = next((x for x in sorted(_TLD, key=len, reverse=True) if last.startswith(x)), last)
        return f"{local}@{'.'.join(labels)}".lower()
    return ""
def _phone(text):
    best = None
    for m in re.finditer(r"(?<![\w.])(\+?\(?\d[\d\s\-().]{8,17}\d)(?![\w])", text):
        raw, d = m.group(1).strip(), re.sub(r"\D", "", m.group(1))
        if re.search(r"(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}", raw):
            continue
        if len(d) in (10, 11, 12) and d[-10] in "6789" and (len(d) == 10 or d[:-10] in ("91", "0")):
            norm = f"+91 {d[-10:-5]} {d[-5:]}"
        elif 11 <= len(d) <= 13 and raw.startswith("+") or len(d) == 10 and re.fullmatch(r"\(?\d{3}\)?[\s.-]?\d{3}[\s.-]\d{4}", raw):
            norm = re.sub(r"\s+", " ", raw)
        else:
            continue
        score = 3 if re.search(r"(?i)(mobile|phone|contact|cell|tel|mob|ph)\W{0,6}$", text[max(0, m.start() - 14):m.start()]) else 2 if m.start() < 700 else 1
        best = best if best and best[0] >= score else (score, norm)
    return best[1] if best else ""
def _name(text, header):
    """label -> first clean 2-4 word header line -> spaCy PERSON -> name from e-mail -> single word. Returns (name, notes)."""
    cands = [("label", m.group(1)) for m in [re.search(r"(?im)^\s*(?:full\s*)?name\s*[:\-]\s*([^\n|@\d]{3,50})", text)] if m]
    cands += [("header", re.split(r"[|•·,;/()\d@]|\s{3,}|\s-\s|:|https?", ln.strip())[0]) for ln in header[:12]]
    doc = _doc("\n".join(header[:10])[:600])
    cands += [("spacy", e.text) for e in doc.ents if e.label_ == "PERSON"] if doc is not None else []
    def valid(c, lo):
        w = re.sub(r"(?i)^(?:mr|mrs|ms|miss|dr|prof|shri|smt|sri)\.?\s+", "", c.strip(" .,-:")).split()
        ok = lo <= len(w) <= 4 and all(re.fullmatch(r"[A-Za-z][A-Za-z.'\-]*", x) for x in w) and sum(map(len, w)) >= 3
        bad = any(x.lower().strip(".") in _NAME_STOP or _ROLE.fullmatch(x) or (_k(x) in _ALIAS and len(x) > 2) for x in w) or _CITY_RE.fullmatch(" ".join(w))
        mixed = any(x[0].islower() for x in w) and any(x[0].isupper() for x in w)
        return " ".join(w) if ok and not bad and not mixed else None
    def title(n):
        return " ".join(w if re.fullmatch(r"(?:[A-Za-z]\.)+", w) else w.title() if w[0].islower() or w.isupper() else w for w in n.split())
    for lo in (2, 1):
        for src, c in cands:
            if (v := valid(c, lo)) and (lo == 2 or src != "header"):
                return title(v), ["name via spaCy NER"] * (src == "spacy")
        parts = [p for p in re.split(r"[._\-+\d]+", _email(text).split("@")[0]) if len(p) > 1]
        if len(parts) >= (2 if lo == 2 else 1):
            return title(" ".join(parts[:3])), ["name derived from e-mail address"]
    return "", ["name not found"]
def _location(text, header):
    m = re.search(r"(?im)^\s*(?:current\s*|present\s*|preferred\s*)?(?:location|city|address|place)\s*[:\-]\s*([^\n]{3,90})", text)
    if m and not _CITY_RE.search(m.group(1)):
        return ", ".join(p.strip() for p in re.sub(r"\d+", "", m.group(1)).split(",")[-2:] if p.strip())[:60]
    c = _CITY_RE.search(m.group(1)) if m else next((c for c in (_CITY_RE.search("\n".join(header[:12])), _CITY_RE.search(text[:1500]), _CITY_RE.search(text)) if c), None)
    return ", ".join(x for x in c.groups() if x) if c else ""
def _entries(exp, today):
    """Work history: each date range anchors one job; company/role come from the same line or the lines around it."""
    lines, out, hits = exp.split("\n"), [], []
    for i, ln in enumerate(lines):
        rs, prev_end = _ranges(ln, today), 0
        for a, b, m in rs:
            seg = ln[prev_end:m.start()] if len(rs) > 1 else ln[:m.start()] + " " + ln[m.end():]
            hits.append((i, a, b, m, " ".join(seg.split()[-6:]) if len(seg) > 80 else seg.strip(" |,-–—:()[]•")))
            prev_end = m.end()
    for k, (i, a, b, m, before) in enumerate(hits):
        prev = [x.strip(" •") for x in lines[max(0, i - 2):i] if x.strip() and not _RANGE.search(x)]
        nxt_line = lines[i + 1].strip(" •") if i + 1 < len(lines) and not _RANGE.search(lines[i + 1]) else ""
        pieces = [re.sub(r"(?i)^(?:(?:and|worked|working|currently|as|at|with|for|in)\s+)+|\s+(?:from|since|during|between|in)$", "", p).strip(" ,.") for blk in ([before] if before else []) + prev[::-1] + [nxt_line] * (not before and not prev)
                  for p in re.split(r"\s[|•·@\-–—]\s|\s+at\s+|\s{2,}", blk) if p.strip(" ,.")]
        role = next((p for p in pieces if _ROLE.search(p) and len(p) < 70), "")
        used_next = not role and bool(_ROLE.search(nxt_line)) and len(nxt_line) < 70 and not _COMP.search(nxt_line)
        role = nxt_line if used_next else role
        comp = next((p for p in pieces if p != role and _COMP.search(p) and len(p) < 70), "") or next(
            (p for p in pieces if p != role and not _CITY_RE.fullmatch(p) and len(p.split()) <= 6 and not re.search(r"\d", p) and p[:1].isupper()), "")
        comp = re.sub(r"[,\-–]\s*(?:%s)\W*$" % "|".join(map(re.escape, _CITIES)), "", comp)
        role, comp = _cl(role), _cl(comp); comp = "" if re.search(r"(?i)business use only|confidential|proprietary|^(?:pvt|private|ltd|limited|inc|llc|technologies|solutions|services)\.?(?:\s+(?:ltd|limited|pvt))?\.?$", comp) or comp.lower().strip(" .") in ("working", "present", "current", "currently", "employed", "experience", "company", "organization", "client", "project", "projects", "role", "till date", "summary") else comp
        nxt = hits[k + 1][0] if k + 1 < len(hits) else len(lines)
        nb = k + 1 < len(hits) and hits[k + 1][4] == "" and hits[k + 1][0] != i
        end = max(i + 1 + used_next, nxt - 2) if nb else nxt
        now, e_s = bool(re.match(_NOW, m.group(2), re.I)), "Present" if re.match(_NOW, m.group(2), re.I) else _fmt(b)
        out.append({"company": comp, "role": role, "start_date": _fmt(a), "end_date": e_s, "duration": f"{_fmt(a)} - {e_s}", "location": (_CITY_RE.search(" ".join(pieces)) or [None, ""])[1],
                    "description": " ".join(x.strip(" •") for x in lines[i + 1 + used_next:end] if x.strip())[:700] if hits[k][0] != (hits[k + 1][0] if k + 1 < len(hits) else -1) else "", "_iv": (a, b)})
    return out
_DEG = re.compile(r"\b(B\.?\s?Tech|M\.?\s?Tech|B\.?E\.?|M\.?E\.?|B\.?Sc|M\.?Sc|B\.?Com|M\.?Com|BCA|MCA|BBA|MBA|PGDM|B\.?A\.?|M\.?A\.?|Ph\.?D|Bachelor[^\n,;|]{0,45}|Master[^\n,;|]{0,45}|Diploma[^\n,;|]{0,40}|Intermediate|HSC|SSC|12th|10th)(?![a-z])")
_INST = re.compile(r"(?i)\b(university|college|institute|school|academy|iit|nit|iiit|bits|polytechnic|vidyalaya|board)\b")
def _education(text):
    lines, out = [x.strip(" •") for x in text.split("\n")], []
    for i, ln in enumerate(lines):
        m = _DEG.search(ln)
        if not m or len(ln) > 220:
            continue
        nx = lines[i + 1] if i + 1 < len(lines) and not _DEG.search(lines[i + 1]) else ""
        pv = lines[i - 1] if i and not nx and not _DEG.search(lines[i - 1]) and not re.search(r"20\d{2}", ln) else ""
        seg, win = re.split(r"\s[|\-–—]\s|,|\|", ln[m.start():]), " ".join((ln, nx, pv))
        inst = next((p.strip() for p in seg[1:] if _INST.search(p)), "") or next((x for x in lines[i + 1:i + 3] + lines[max(0, i - 1):i] if _INST.search(x) and not _DEG.search(x)), "")
        yrs = sorted({int(y) for y in re.findall(r"\b(?:19[89]\d|20[0-4]\d)\b", win)})
        g = re.search(r"\d(?:\.\d+)?\s*/\s*10|(?:CGPA|GPA)\s*[:\-]?\s*\d(?:\.\d+)?|\d(?:\.\d+)?\s*(?:CGPA|GPA)|\d{2}(?:\.\d+)?\s*%", win, re.I)
        out.append({"degree": seg[0].strip()[:80], "institute": inst[:90], "start_year": str(yrs[0]) if len(yrs) > 1 else "", "end_year": str(yrs[-1]) if yrs else "",
                    "grade": g.group().strip() if g else "", "location": (_CITY_RE.search(win) or [None, ""])[1]})
    return out[:6]
def _projects(text):
    blocks = [b for b in re.split(r"\n\s*\n|\n(?=\s*(?:Project|PROJECT)\s*(?:Name|Title|\d+)?\s*[:\-])", text) if b.strip()]
    out = []
    for b in blocks[:8]:
        ls = [x.strip(" •-*") for x in b.split("\n") if x.strip()]
        ts = re.search(r"(?i)(?:tech(?:nologies)?(?: stack)?|environment|tools|stack)\s*[:\-]\s*([^\n]+)", b)
        out.append({"project_name": re.sub(r"(?i)^project(?: name| title)?\s*[:\-]?\s*", "", ls[0])[:100], "role": "", "organization": "", "start_date": "", "end_date": "",
                    "description": " ".join(ls[1:])[:500], "tech_stack": ts.group(1).strip() if ts else ", ".join(extract_skills(b, use_nlp=False)[:8])})
    return out
# ---------------------------------------------------------------- resume parser
def parse_resume(text, today=None):
    """Raw resume text -> dict in the schema the Groq prompt used. Empty / scanned input -> {'error': ..., 'parsed': False}."""
    today, t = today or date.today(), _clean(text)
    if len(t) < 50 or len(re.findall(r"[A-Za-z]{3,}", t)) < 15:
        return {"error": "insufficient_text: empty or scanned/image-only document (run OCR first)", "parsed": False}
    secs, lines = _sections(t), [x for x in t.split("\n") if x.strip()]
    header = [x for x in secs.get("header", "").split("\n") if x.strip()] or lines[:12]
    name, notes = _name(t, header)
    parts, ini = name.split(), 0
    while ini < len(parts) - 1 and re.fullmatch(r"[A-Za-z]\.?", parts[ini]):
        ini += 1
    first = "".join(p if p.endswith(".") else p + "." for p in parts[:ini]) if ini > 1 else (parts[0] if parts else "")
    rest = parts[ini:] if ini > 1 else parts[1:]
    email, phone = _email(t), _phone(t)
    notes += ["email not found"] * (not email) + ["phone not found"] * (not phone)
    url = lambda p: (lambda m: (m.group().rstrip(".") if m.group().lower().startswith("http") else "https://" + m.group().rstrip(".")) if m else "")(re.search(p, t, re.I))
    exp = secs.get("experience", "")
    ents = _entries(exp, today) if exp else []
    scope = exp if len(exp) > 40 else "\n".join(v for k, v in secs.items() if k not in ("education", "projects", "certs"))
    rng = [(a, b) for a, b, m in _ranges(scope, today) if len(exp) > 40 or not _DEG.search(scope[max(0, m.start() - 60):m.end() + 40])]
    if not ents:
        ents = [{"company": "", "role": "", "start_date": _fmt(a), "end_date": _fmt(b), "duration": f"{_fmt(a)} - {_fmt(b)}", "location": "", "description": "", "_iv": (a, b)} for a, b in rng[:8]]
    yrs = round(_union([e["_iv"] for e in ents] or rng) / 12 + 1e-4, 1)
    claim = max([float(x) for x in re.findall(r"(?i)(\d{1,2}(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:total\s+|relevant\s+|professional\s+|work\s+|industry\s+)?(?:experience|exp)", t)] or [0])
    yoe = min(50.0, claim if claim > yrs + 2 or not yrs else yrs)          # explicit "X years" wins only when date ranges are clearly incomplete
    ranked, counts = extract_skills(t, with_counts=True)
    for s in extract_skills(secs.get("skills", ""), use_nlp=False):
        counts[s] = counts.get(s, 0) + 2
    skills = sorted(ranked, key=lambda s: (-counts[s], ranked.index(s)))[:100]
    ent_sk = [set(extract_skills(f"{e['company']} {e['role']} {e['description']}", use_nlp=False)) for e in ents]
    rel = []
    for s in skills[:25]:
        ex = re.search(rf"(?i)(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience\s*)?(?:in|with|on)?\s*{re.escape(s)}\b|\b{re.escape(s)}\b\s*[(\-:]\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", t)
        y = float(next(g for g in ex.groups() if g)) if ex else round(_union([e["_iv"] for e, k in zip(ents, ent_sk) if s in k]) / 12, 1)
        rel += [{"skill": s, "years": min(y, yoe) if yoe else y}] * (y > 0)
    cur = next((e for e in ents if e["end_date"] == "Present"), ents[0] if ents else None)
    desig = (cur or {}).get("role", "") or next((m.group().strip(" .") for ln in header[:8] if "@" not in ln for m in [re.search(r"[A-Z][\w+#./ ]{0,40}" + _ROLE.pattern, ln, re.I)] if m), "")
    nm = re.search(r"(?i)notice\s*period\s*[:\-]?\s*(\d+)\s*(day|week|month)|(\d+)\s*(day|week|month)s?\s*notice", t)
    nd = int([g for g in nm.groups() if g and g.isdigit()][0]) * {"day": 1, "week": 7, "month": 30}[[g for g in nm.groups() if g and not g.isdigit()][0]] if nm else 0
    ctc = lambda lab: (re.search(rf"(?i)(?:{lab})\s*(?:ctc|salary|compensation)\s*[:\-]?\s*((?:rs\.?|inr|usd|\$|₹)?\s*[\d.,]+\s*(?:lpa|lakhs?|lacs?|l\b|k\b|cr\b|per annum|pa\b)?)", t) or [None, ""])[1].strip()
    edu = _education(secs.get("education") or "\n".join(l for l in lines if _DEG.search(l)))
    certs = [c.strip(" •-*") for c in secs.get("certs", "").split("\n") if 4 < len(c.strip(" •-*")) < 120 and not re.search(r"(?i)notice|ctc|salary|expected|:\s*\d", c)][:15]
    certs += [m.group().strip() for m in re.finditer(r"\b(?:AWS|Azure|Google Cloud|GCP|Oracle|SAP|Salesforce|Cisco)\s+Certified[^\n.,;|]{0,50}|\b(?:PMP|CSM|CISSP|CEH|CCNA|CCNP|PRINCE2|ITIL(?: Foundation| v4)?)\b", t) if m.group().strip() not in certs]
    for e in ents:
        e.pop("_iv")
    return {"first_name": first, "middle_name": " ".join(rest[:-1]), "last_name": rest[-1] if rest else "", "email": email, "phone": phone,
            "address": (re.search(r"(?im)^\s*address\s*[:\-]\s*([^\n]{5,150})", t) or [None, ""])[1].strip(), "location": _location(t, header),
            "pincode": (re.search(r"\b[1-9]\d{2}\s?\d{3}\b", re.sub(r"\+?91[\s\-]*[6-9]\d{9}|\d{7,}", "", t)) or [""])[0].replace(" ", "") if re.search(r"(?i)pin\s*(?:code)?|address|location", t) else "",
            "linkedin": url(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|pub|company)/[\w\-%.]+/?"), "other_social": url(r"(?:https?://)?(?:www\.)?(?:github\.com|gitlab\.com|behance\.net)/[\w\-./]+"),
            "current_role": desig, "designation": desig, "current_company": (cur or {}).get("company", ""), "current_ctc": ctc("current|present"), "expected_ctc": ctc("expected|expecting"),
            "years_of_experience": yoe, "notice_period_days": nd,
            "employment_status": "Freelancer" if cur and re.search(r"(?i)freelanc", cur["role"] + cur["description"]) else "Employed" if cur and cur["end_date"] == "Present" else "Student" if not ents and edu else "",
            "core_skills": skills, "relevant_experience": rel, "education": edu, "certifications": certs[:20], "work_experience": ents[:12],
            "projects": _projects(secs["projects"]) if secs.get("projects") else [], "summary": re.sub(r"\s+", " ", secs.get("summary", ""))[:800],
            "parser": "nlp_engine", "parsed": True, "extraction_notes": notes}
# ---------------------------------------------------------------- JD matching: TF-IDF cosine + fuzzy skill gap
_STOP = list(ENGLISH_STOP_WORDS | set("responsibilities responsibility requirements requirement required preferred candidate candidates looking ability strong good excellent knowledge work working team "
                                      "teams years year experience role job position company skills skill including etc plus must should will able well across using use ideal join opportunity apply description "
                                      "mandatory desired minimum relevant proven demonstrated understanding passion environment seeking hiring".split()))
_NICE = re.compile(r"(?i)\b(nice to have|good to have|preferred|desirable|plus|bonus|optional|added advantage)\b")
def analyze_match(resume_text, jd_text, today=None):
    """Deterministic resume-vs-JD analysis. Output keys mirror the Groq JSON that /api/analyze-match consumed, plus an explicit missing_skills list."""
    r, j = _clean(resume_text), _clean(jd_text)
    if len(r) < 50 or len(j) < 30:
        return {"error": "insufficient_text", "match_score": 0, "matching_skills": [], "missing_skills": []}
    rs = extract_skills(r)
    have = set(rs) | {x for s in rs for x in _IMPLIES.get(s, [])}
    jd_order = extract_skills(j)
    jd_w = {s: 1.0 for s in jd_order}
    for ln in j.split("\n"):                           # lines marked nice-to-have / preferred count half
        for s in extract_skills(ln, use_nlp=False):
            jd_w[s] = min(jd_w.get(s, 1.0), 0.5) if _NICE.search(ln) else jd_w.get(s, 1.0)
    jd_sk = jd_order + [s for s in jd_w if s not in jd_order]
    matching, missing = [s for s in jd_sk if s in have], [s for s in jd_sk if s not in have]
    cover = sum(jd_w[s] for s in matching) / sum(jd_w.values()) * 100 if jd_w else None
    sk_tok = lambda text, sk: text.lower() + " " + " ".join("sk_" + re.sub(r"\W", "", s.lower()) for s in sk)     # React.js == ReactJS
    vec = TfidfVectorizer(stop_words=_STOP, ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b[a-z][a-z0-9_+#.]*[a-z0-9+#]\b|\b[a-z]\b")
    try:
        m = vec.fit_transform([sk_tok(j, jd_sk), sk_tok(r, sorted(have))])
        cos = float(cosine_similarity(m[0], m[1])[0, 0])
    except ValueError:
        cos = 0.0
    tfidf = min(100.0, cos / 0.55 * 100)               # 0.55 cosine on keyword-sparse text ~ an excellent fit
    parsed = parse_resume(r, today)
    yrs = parsed.get("years_of_experience", 0)
    need = re.search(r"(?i)(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:years?|yrs?)", j)
    need = float(need.group(1)) if need else 0
    exp = 100 if need and yrs >= need else round(yrs / need * 100) if need else min(100, round(yrs * 10))
    lvl = lambda s: max([v for k, v in (("phd", 5), ("doctorate", 5), ("master", 4), ("m.tech", 4), ("mba", 4), ("mca", 4), ("m.sc", 4), ("bachelor", 3), ("b.tech", 3), ("b.e", 3), ("bca", 3), ("b.sc", 3), ("diploma", 2)) if k in s.lower()] or [0])
    jl, rl = lvl(j), max([lvl(e["degree"]) for e in parsed.get("education", [])] or [lvl(r)])
    edu = 100 if rl and rl >= jl else 60 if rl and jl - rl == 1 else 30 if jl else 70 if rl else 40
    cj = set(re.findall(r"(?i)\b(?:pmp|csm|cissp|ceh|ccna|itil|prince2|aws certified|azure certified|sap certified)\b", j))
    cert = round(len([c for c in cj if c.lower() in r.lower()]) / len(cj) * 100) if cj else 70
    sk = cover if cover is not None else tfidf
    score = round(0.6 * sk + 0.4 * tfidf) if cover is not None else round(tfidf)
    score = max(0, min(100, round(0.85 * score + 0.15 * exp) if need else score))
    rec = "Shortlisted" if score >= 85 else "Strong Match" if score >= 70 else "Moderate Match" if score >= 50 else "Low Match" if score >= 30 else "Not Recommended"
    text = (f"Match score {score}/100 ({rec}). Skill coverage {'n/a' if cover is None else round(cover)}%, TF-IDF similarity {round(tfidf)}%, experience fit {exp}%. "
            f"{len(matching)} of {len(jd_sk)} JD skills found in the resume; {len(missing)} missing.")
    return {"match_score": score, "recommendation": rec,
            "category_scores": {"skills_match": round(sk), "experience_match": exp, "education_match": edu, "certifications_match": cert, "overall_fit": score},
            "matching_skills": matching, "missing_skills": missing,
            "strengths": ([f"Covers {len(matching)} of {len(jd_sk)} JD skills: {', '.join(matching[:6])}"] if matching else []) + ([f"{yrs:g} yrs meets the {need:g}+ yr requirement"] if need and yrs >= need else []),
            "weaknesses": ([f"Missing JD skills: {', '.join(missing[:6])}"] if missing else []) + ([f"Experience ({yrs:g} yrs) below the {need:g}+ yrs requested"] if need and yrs < need else []),
            "detailed_analysis": text, "executive_summary": text, "tfidf_similarity": round(tfidf, 1), "skill_coverage": None if cover is None else round(cover, 1),
            "resume_skills": rs, "jd_skills": jd_sk, "years_of_experience": yrs, "parser": "nlp_engine",
            "pre_screening_questions": [f"Describe your hands-on experience with {s}. What did you build or support?" for s in missing[:3]] + ["Which project best demonstrates your fit for this role?"]}
