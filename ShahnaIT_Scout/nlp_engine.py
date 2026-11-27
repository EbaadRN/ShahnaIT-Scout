"""nlp_engine.py - ShahnaIT Scout's offline resume parser and JD matcher (no external AI calls).

Public API (stable, used by app.py / backfill.py):
    extract_text(path, filename=None)          -> clean text from a PDF / DOCX / TXT file
    parse_resume(text, today=None, filename=None) -> dict in the schema the UI expects
    analyze_match(resume_text, jd_text, today=None, resume_filename=None) -> explainable match report
    parse_jd(text)                              -> structured job requirements
    extract_skills(text, use_nlp=True, with_counts=False) -> canonical skill names

Design notes
  * Deterministic: same input -> same output. No network, no LLM, no heavy models.
  * PDF text comes from PyMuPDF (accurate word spacing); PyPDF2 is only a fallback.
  * DOCX text includes tables, text boxes, headers and footers in reading order
    (many resumes keep the name / phone / e-mail inside a table or header).
  * Every heuristic below was written against real resumes that failed before; keep the
    tests in mind when changing a rule.
"""
import io
import os
import re
import unicodedata
import zipfile
from datetime import date

try:
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:                                    # matcher still works (without the TF-IDF component)
    TfidfVectorizer = None
    ENGLISH_STOP_WORDS = frozenset()

__all__ = ["extract_text", "parse_resume", "analyze_match", "parse_jd", "extract_skills"]
ENGINE_VERSION = "2.0"

# =====================================================================================
# 1. TEXT EXTRACTION
# =====================================================================================
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"


def _pdf_text(data):
    """PyMuPDF first (correct spacing, reading order); PyPDF2 as fallback."""
    text = ""
    try:
        import pymupdf as _fitz                      # PyMuPDF >= 1.24
    except Exception:
        try:
            import fitz as _fitz                     # older PyMuPDF
        except Exception:
            _fitz = None
    if _fitz is not None:
        try:
            doc = _fitz.open(stream=data, filetype="pdf")
            pages = []
            for page in doc:
                pages.append(page.get_text("text"))
            doc.close()
            text = "\n".join(pages)
        except Exception:
            text = ""
    if len(re.findall(r"[A-Za-z]{3,}", text)) < 20:
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(data))
            alt = "\n".join((p.extract_text() or "") for p in reader.pages)
            if len(alt) > len(text):
                text = alt
        except Exception:
            pass
    return text


def _docx_lines_from(el, out):
    """Walk a WordprocessingML element in document order: paragraphs, tables (cell by cell),
    content controls and text boxes. mc:Fallback copies are skipped (they duplicate text boxes)."""
    for ch in el:
        tag = ch.tag
        if tag == _W + "p":
            buf, boxes = [], []
            for node in ch.iter():
                t = node.tag
                if t == _MC + "Fallback":
                    continue
                if t == _W + "txbxContent":
                    boxes.append(node)
            skip = set()
            for b in boxes:
                for n in b.iter():
                    skip.add(n)
            for fb in ch.iter(_MC + "Fallback"):
                for n in fb.iter():
                    skip.add(n)
            for node in ch.iter():
                if node in skip:
                    continue
                t = node.tag
                if t == _W + "t" and node.text:
                    buf.append(node.text)
                elif t in (_W + "tab",):
                    buf.append("  ")
                elif t in (_W + "br", _W + "cr"):
                    buf.append("\n")
            line = "".join(buf)
            if line.strip():
                out.extend(line.split("\n"))
            else:
                out.append("")
            for b in boxes:
                _docx_lines_from(b, out)
        elif tag == _W + "tbl":
            for row in ch.findall(_W + "tr"):
                for cell in row.findall(_W + "tc"):
                    _docx_lines_from(cell, out)
                out.append("")
        elif tag == _W + "sdt":
            content = ch.find(_W + "sdtContent")
            _docx_lines_from(content if content is not None else ch, out)
        elif tag in (_W + "customXml", _W + "smartTag", _W + "ins", _W + "hyperlink"):
            _docx_lines_from(ch, out)


def _docx_text(data):
    try:
        from lxml import etree
    except Exception:
        etree = None
    lines = []
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        names = z.namelist()
        parts = sorted(n for n in names if re.match(r"word/header\d*\.xml$", n))
        parts += ["word/document.xml"]
        parts += sorted(n for n in names if re.match(r"word/footer\d*\.xml$", n))
        seen_hf = set()
        for name in parts:
            if name not in names:
                continue
            raw = z.read(name)
            if etree is not None:
                root = etree.fromstring(raw)
            else:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(raw)
            body = root.find(_W + "body") if name == "word/document.xml" else root
            chunk = []
            _docx_lines_from(body if body is not None else root, chunk)
            key = "\n".join(x.strip() for x in chunk if x.strip())
            if name != "word/document.xml":
                if not key or key in seen_hf:
                    continue
                seen_hf.add(key)
            lines.extend(chunk)
            lines.append("")
    except Exception:
        try:
            import docx
            d = docx.Document(io.BytesIO(data))
            lines = [p.text for p in d.paragraphs]
            for t in d.tables:
                for r in t.rows:
                    for c in r.cells:
                        lines.append(c.text)
        except Exception:
            return ""
    out, prev = [], None
    for ln in lines:                                 # drop consecutive duplicates (merged cells repeat text)
        s = ln.rstrip()
        if s and s == prev:
            continue
        out.append(s)
        prev = s if s else prev
    return "\n".join(out)


def extract_text(path, filename=None):
    """Best-quality plain text from a resume / JD file. Accepts a path or raw bytes (then pass filename)."""
    if isinstance(path, (bytes, bytearray)):
        data, name = bytes(path), (filename or "")
    else:
        name = filename or str(path)
        with open(path, "rb") as fh:
            data = fh.read()
    ext = os.path.splitext(name)[1].lower().lstrip(".")
    if not ext:
        ext = "pdf" if data[:4] == b"%PDF" else "docx" if data[:2] == b"PK" else "txt"
    if ext == "pdf":
        text = _pdf_text(data)
    elif ext in ("docx", "docm", "dotx"):
        text = _docx_text(data)
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("latin-1", "ignore")
    return _clean(text)


# =====================================================================================
# 2. NORMALISATION
# =====================================================================================
_BULLETS = "●•▪■□◦○◆◇►▸▶➢➤➣➔→✓✔✗❖❑❒⦿⚫⚬∙·◉◘\uf0b7\uf0a7\uf0d8\uf076\uf0fc\uf0a8\uf02d\uf0e0\uf0f0\uf0de\uf097\uf06e\uf06c\uf075\uf0b2"
_BULLET_RE = re.compile("[" + re.escape(_BULLETS) + "]")


def _clean(text):
    t = unicodedata.normalize("NFKC", text or "")
    t = t.replace("\r\n", "\n").replace("\r", "\n").replace("\x0c", "\n").replace("\t", "  ")
    t = re.sub(r"[\u200b-\u200f\u00ad\ufeff\u2060\u202a-\u202e]", "", t)
    t = t.replace("\u00a0", " ").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = _BULLET_RE.sub("•", t)
    t = re.sub(r"(?m)^[ \t]*[\-\*o][ \t]+(?=[A-Z])", "• ", t)          # '- Did X' / 'o Did X' bullets
    t = re.sub(r"(?i)(linkedin\.com/(?:in|pub)/[\w\-%]*-)\s*\n\s*(?=\w)", r"\1", t)   # keep hyphens in wrapped LinkedIn URLs
    t = re.sub(r"(?<=[A-Za-z])-\n(?=[a-z])", "", t)                     # de-hyphenate PDF line wraps
    t = re.sub(r"(?<=[A-Za-z]) -(?=[a-z]{2})", "-", t)                  # PyPDF2 'hands -on', 'multi -stage'
    t = re.sub(r"(?m)^[ \t]*•[ \t]*\n[ \t]*(?=\S)", "• ", t)            # lone bullet line + text on next line
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _k(s):
    """Normalisation key: 'React.js' == 'ReactJS' == 'react js'; keeps + and # (C++, C#); '.NET' -> 'dotnet'."""
    s = s.strip().lower()
    s = re.sub(r"^\.(?=[a-z])", "dot", s)
    return re.sub(r"[^a-z0-9+#]", "", s)


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


_SMALL = {"of", "and", "the", "in", "for", "on", "at", "to", "a", "an", "with", "by", "&"}
_KEEP_UPPER = set("IT CE UI UX QA QC HR AI ML BI IBM HCL TCS NTT SAP SFCC SFRA CRM ERP USA UK UAE KSA GCC LLC LLP EEE ECE CSE ME CE MBA MCA BCA BBA "
                  "B2B B2C AMS OSF SMC TLG DXC CGI EY KPMG PWC LTI PS AWS GCP API SDK SME VP CTO CEO CFO COO II III IV DB RPA ETL BPO KPO IOT "
                  "SQL NET MNC IIT NIT VTU JNTU KITS BITS VIT SRM KL ASP CPQ CPI BTP ABAP HANA PI PO FICO MM SD PP HCM SCM BW BO "
                  "GIS ICT ITES ITIL OEM PMO NOC SOC CRM".split())


def _smart_title(s):
    """'SENIOR TECH LEAD WIPRO LTD.' -> 'Senior Tech Lead Wipro Ltd.'; leaves mixed-case text untouched."""
    s = re.sub(r"\s+", " ", (s or "").strip())
    letters = re.sub(r"[^A-Za-z]", "", s)
    if not letters:
        return s
    upper_ratio = sum(c.isupper() for c in letters) / len(letters)
    lower_words = [w for w in s.split() if w[:1].islower()]
    if upper_ratio < 0.75 and not (len(lower_words) == len(s.split())):
        return s
    out = []
    for i, w in enumerate(s.split()):
        core = re.sub(r"[^A-Za-z0-9]", "", w)
        if core.upper() in _KEEP_UPPER or (len(core) <= 2 and core.isalpha() and core.upper() not in ("OF", "IN", "AT", "TO", "ON", "AN", "BY")) or re.search(r"\d", core):
            out.append(w.upper() if core.upper() in _KEEP_UPPER else w)
        elif core.lower() in _SMALL and i:
            out.append(w.lower())
        else:
            out.append(re.sub(r"[A-Za-z][A-Za-z']*", lambda m: m.group(0)[0].upper() + m.group(0)[1:].lower(), w))
    return " ".join(out)


# =====================================================================================
# 3. SKILLS TAXONOMY
#    One line per family:  FAMILY: Canonical|alias|alias, Canonical|alias ...
#    alias prefixes:  ~ = ambiguous word, counts only in skill lists / skills sections
#                     ^ = case-sensitive (must appear exactly as written)
# =====================================================================================
_SKILL_DATA = r"""
LANG: Python|Python3|Python 3, Java|Core Java|Java 8|Java 11|Java 17|J2EE|JEE|Java EE, JavaScript|^JS|ECMAScript|ES6|ES6+|Java Script|Javascript (ES6+), TypeScript|~^TS, ^C|~^C Language, C++|CPP, C#|CSharp|C Sharp, ~^Go|Golang, ~^Rust, Ruby, PHP, ~^Swift, Kotlin, Scala, ~^R|R Programming, Perl, Dart, Objective-C|ObjC, MATLAB, Julia, Lua, Haskell, Elixir, Erlang, Clojure, F#, Groovy, COBOL, Fortran, VBA, VBScript, Visual Basic|VB.NET|VB6, PowerShell, Bash|Shell Scripting|Unix Shell|Shell Script|Bash Scripting, SQL, PL/SQL|PLSQL, T-SQL|TSQL, HTML|HTML5, CSS|CSS3, SASS|SCSS, LESS, XML, JSON, YAML, GraphQL, Solidity, ABAP|ABAP/4|ABAP 4, ABAP OO|Object Oriented ABAP|OO ABAP|OOPS ABAP|ABAP Objects, ABAP 7.4+ Syntax|New Syntax 7.4|ABAP 7.4|ABAP 7.5|New ABAP Syntax, Verilog, VHDL, SystemVerilog, WebAssembly, Regex|Regular Expressions, SAS, Stata, SPSS, Apex|Apex Programming, ISML, SOQL, SOSL, Ampscript
FRONTEND: React|React.js|ReactJS|React JS, Angular|AngularJS|Angular.js|Angular JS, Vue.js|VueJS|Vue JS|~^Vue, Svelte, Next.js|NextJS|Next JS, Nuxt.js, Redux|Redux Toolkit, MobX, NgRx, jQuery, Bootstrap, Tailwind CSS|TailwindCSS|Tailwind, Material UI|MUI, Chakra UI, ~^Foundation|Zurb Foundation, Ant Design, Webpack, Vite, Babel, Storybook, Ember.js, Backbone.js, Three.js, D3.js, Chart.js, Highcharts, Electron, PWA|Progressive Web Apps|Progressive Web App, Responsive Web Design|Responsive Design|Responsive Web Development, Web Accessibility|WCAG, Cross-Browser Compatibility|Cross Browser Compatibility|Cross-Browser, RxJS, Handlebars, Thymeleaf, Jinja2, Lodash, Axios, Socket.IO, WebSockets|WebSocket, WebRTC, Micro Frontends, Styled Components, Figma, Adobe XD, Sketch, Photoshop|Adobe Photoshop, Illustrator|Adobe Illustrator, ~^InDesign, Canva, UI Design, UX Design|UI/UX|User Experience Design, Wireframing, Prototyping, W3C Standards|W3C
BACKEND_JS: Node.js|NodeJS|Node JS|~^Node, Express.js|ExpressJS|Express JS|~^Express, NestJS, Koa, Fastify
BACKEND_PY: Django, Django REST Framework, Flask, FastAPI, Celery, Pandas, NumPy, SciPy
BACKEND_JAVA: ~^Spring|Spring Framework, Spring Boot|SpringBoot, Spring MVC, Spring Security, Spring Cloud, Spring Data, Hibernate, JPA, JDBC, MyBatis, Struts, JSF, Servlets|Servlet, JSP, Maven, Gradle, ~^Ant, Microservices|Micro Services|Microservice, Kafka|Apache Kafka, Quarkus, Micronaut, Vert.x, Tomcat|Apache Tomcat, JBoss|WildFly, WebLogic, WebSphere
DOTNET: .NET|.NET Core|DotNet|.Net Framework|ASP.NET|ASP.NET Core|ASP.NET MVC, Entity Framework, LINQ, Blazor, WCF, WPF, WinForms, Xamarin
WEB: REST|RESTful|REST API|REST APIs|RESTful API|RESTful APIs|RESTful Services|~^Rest, SOAP|SOAP API|SOAP Web Services, Web Services, gRPC, OAuth|OAuth2|OAuth 2.0, JWT, SAML, SSO|Single Sign-On, Swagger|OpenAPI, Postman, RabbitMQ, ActiveMQ, MQTT, JMS, API Gateway, API Management|APIM, Apigee|Apigee Edge|Apigee X, MuleSoft|Mule ESB|Mule 4, WSO2, TIBCO, Dell Boomi|Boomi|Dell Bhoomi, Kong, Laravel, Symfony, CodeIgniter, WordPress, Drupal, Magento, Shopify, WooCommerce, Ruby on Rails|Rails, Headless Commerce|Headless
MOBILE: Android|Android SDK|Android Development, iOS|iOS Development, React Native, Flutter, Ionic, Cordova, SwiftUI, Jetpack Compose, Xcode, Android Studio, Firebase, Unity|~^Unity 3D, Unreal Engine
DATABASE: MySQL, PostgreSQL|Postgres, SQL Server|MSSQL|MS SQL|Microsoft SQL Server|MS SQL Server, Oracle Database|Oracle DB|Oracle 11g|Oracle 12c|Oracle 19c|Oracle SQL, ~^Oracle, MongoDB|Mongo DB|Mongo, Redis, Cassandra, DynamoDB, Elasticsearch|Elastic Search, OpenSearch, Solr, Neo4j, CouchDB, Couchbase, MariaDB, SQLite, DB2|IBM DB2, Teradata, Snowflake, BigQuery, Redshift, Hive, HBase, Cosmos DB|CosmosDB|Azure Cosmos DB, Firestore, Aurora, ~RDS|Amazon RDS, Memcached, InfluxDB, ClickHouse, Sybase, NoSQL, RDBMS, Stored Procedures, Query Optimization, Database Design, Data Modeling|Data Modelling, ~Indexing, ~Sharding, ~Replication
CLOUD_AWS: AWS|Amazon Web Services, EC2|Amazon EC2, S3|Amazon S3, AWS Lambda|~^Lambda, ECS, EKS|Amazon EKS|AWS EKS, Fargate, CloudFormation, CloudWatch, CloudFront, Route 53|Route53, IAM|AWS IAM, VPC|AWS VPC, SNS, SQS, Kinesis, AWS Glue, EMR, SageMaker, Elastic Beanstalk, AWS CodePipeline|CodePipeline, ~ELB|Elastic Load Balancer
CLOUD_AZURE: Azure|Microsoft Azure|MS Azure|Azure Cloud, Azure DevOps|VSTS|Azure DevOps Services|ADO, Azure Functions, AKS|Azure Kubernetes Service, Azure App Service|App Services|Azure App Services|~App Service, Azure SQL|Azure SQL Database, Azure Storage|Azure Blob Storage|Blob Storage, Azure Monitor, Log Analytics, Application Insights|App Insights, Azure Container Registry|~^ACR, Azure Repos, Azure Pipelines|YAML Pipelines, Azure Boards, Azure Key Vault|~Key Vault, Azure Bastion, Azure Load Balancer, Traffic Manager|Azure Traffic Manager, ARM Templates|ARM Template, Bicep, Azure Data Factory|ADF, Azure Synapse|Synapse Analytics, Azure Databricks, Azure AD|Entra ID|Azure Active Directory, Azure Service Bus, Azure Logic Apps|Logic Apps, Azure Virtual Machines, Azure Virtual Network|VNet
CLOUD_GCP: GCP|Google Cloud|Google Cloud Platform, GKE, Cloud Run, Cloud Functions, Dataflow, Dataproc, Pub/Sub, App Engine, Vertex AI
DEVOPS: Docker|Docker Containers, Docker Compose, Kubernetes|K8s|Kube, Helm|Helm Charts, Istio, OpenShift, Rancher, Terraform, Ansible, Ansible Vault, Puppet, ~^Chef, Packer, Vagrant, Jenkins, GitLab CI|GitLab CI/CD, GitHub Actions, CircleCI, Travis CI, Bamboo, TeamCity, ArgoCD|Argo CD, Spinnaker, CI/CD|CI CD|CICD|Continuous Integration|Continuous Delivery|Continuous Deployment, DevOps, DevSecOps, SRE|Site Reliability Engineering, Infrastructure as Code|IaC, Prometheus, Grafana, Datadog, New Relic, Splunk, Dynatrace, AppDynamics, Nagios, Zabbix, ELK Stack|ELK|Elastic Stack, Logstash, Kibana, Fluentd, OpenTelemetry, Nginx, HAProxy, Consul, HashiCorp Vault, JFrog Artifactory|JFrog|Artifactory, Nexus|Sonatype Nexus, SonarQube, SonarCloud, RBAC, Kubernetes Ingress|Ingress Controller|~Ingress, GSLB|Global Server Load Balancing, ~Load Balancing, Linux|~^Unix, RHEL|Red Hat|Red Hat Enterprise Linux, Ubuntu, CentOS, Windows Server, Serverless, Cloud Migration, ~Disaster Recovery, ~High Availability, Containerization
VCS_TOOLS: Git, GitHub, GitLab, Bitbucket, SVN|Subversion, Sourcetree|SourceTree, Jira|JIRA, Confluence, Trello, ~Asana, Monday.com, ServiceNow, Draw.io, Visio|MS Visio|Microsoft Visio, Lucidchart, Miro, Visual Studio|VS Code|Visual Studio Code, IntelliJ|IntelliJ IDEA, Eclipse, PyCharm, Notion
DATA: Apache Spark|PySpark|~^Spark, Hadoop, HDFS, MapReduce, Flink, Airflow|Apache Airflow, NiFi, Sqoop, dbt, Databricks, Delta Lake, ETL, ELT, Data Pipelines|Data Pipeline, Data Engineering, Data Warehousing|Data Warehouse|DWH, Data Lake, Talend, Informatica|Informatica PowerCenter, SSIS, SSRS, SSAS, DataStage|IBM DataStage, Alteryx, Power BI|PowerBI, Tableau, QlikView, Qlik Sense|~^Qlik, Looker, MicroStrategy, Cognos, Excel|MS Excel|Microsoft Excel, Advanced Excel, ~VLOOKUP, ~Pivot Tables, Power Query, DAX, Data Analysis|Data Analytics, Data Visualization, Statistics|Statistical Analysis, Big Data, Jupyter, Matplotlib, Seaborn, Plotly
ML_AI: Machine Learning, Deep Learning, Artificial Intelligence|~^AI, NLP|Natural Language Processing, Computer Vision, TensorFlow, Keras, PyTorch, scikit-learn|sklearn, XGBoost, LightGBM, Hugging Face|HuggingFace, LLM|LLMs|Large Language Models, Generative AI|GenAI|Gen AI, LangChain, LlamaIndex, RAG|Retrieval Augmented Generation, Prompt Engineering, OpenAI|OpenAI API, MLOps, MLflow, Kubeflow, OpenCV, spaCy, NLTK, Data Science, Neural Networks, Agentforce, Einstein AI|Salesforce Einstein
TESTING: Selenium|Selenium WebDriver, Cypress, Playwright, Puppeteer, Appium, TestNG, JUnit, Mockito, PyTest, Jest, Mocha, Jasmine, Karma, Cucumber, BDD, ~^TDD|Test Driven Development, Robot Framework, SoapUI, JMeter, LoadRunner, Gatling, REST Assured|RestAssured, Katalon, TestRail, Zephyr, UFT|QTP, Manual Testing, Automation Testing|Test Automation, Functional Testing, Regression Testing, Performance Testing, Load Testing, ~Smoke Testing, ~Sanity Testing, UAT|User Acceptance Testing, ~Integration Testing, ~Unit Testing, API Testing, Mobile Testing, Security Testing, Black Box Testing|Black-Box Testing, ~Test Cases|Test Case Design, ~Test Planning, Defect Tracking|Bug Tracking, STLC|Software Testing Life Cycle, ISTQB, BrowserStack, System Integration Testing|SIT
SECURITY: Cybersecurity|Cyber Security|Information Security, Network Security, Application Security, OWASP, Vulnerability Assessment, SIEM, QRadar, Incident Response, Burp Suite, Metasploit, Nmap, Wireshark, Nessus, Firewall|Firewalls, Palo Alto, Fortinet|FortiGate, Okta, CyberArk, ISO 27001, GDPR, HIPAA, PCI DSS, NIST, Penetration Testing|Pen Testing|VAPT, IAM Governance|Identity and Access Management, ~Compliance, ~Audit
INFRA: TCP/IP, ~^DNS, DHCP, BGP, OSPF, VLAN, ~^LAN, ~^WAN, Routing and Switching, Cisco, Juniper, CCNA, CCNP, VMware|vSphere|ESXi, Hyper-V, Citrix, Active Directory, LDAP, Office 365|Microsoft 365|O365|MS Office 365, SharePoint, Intune, SCCM, ITIL, ITSM, BMC Remedy, ~Help Desk, ~Technical Support, ~Troubleshooting, ~Patch Management, ~System Administration, Embedded C, RTOS, Arduino, Raspberry Pi, PLC, SCADA, ~^HMI, IoT, AutoCAD, SolidWorks, CATIA, ANSYS, MS Word|Microsoft Word, PowerPoint|MS PowerPoint|Power Point|Microsoft PowerPoint, MS Office|Microsoft Office
SAP_TECH: SAP ABAP|ABAP on HANA|SAP ABAP on HANA|SAP ABAP/4|ABAP Development, SAP HANA|~^HANA|HANA DB, SAP S/4HANA|S/4HANA|S4HANA|S/4 HANA|SAP S4 HANA|SAP S/4|S4 HANA|S/4HANA Cloud, SAP ECC|~^ECC|ECC 6.0, CDS Views|CDS View|Core Data Services|~^CDS, AMDP, SAP RAP|RESTful Application Programming Model|RESTful ABAP Programming|ABAP RAP|~^RAP, SAP CAP|Cloud Application Programming Model, OData|OData V2|OData V4|OData Services, SAP Gateway|SAP NetWeaver Gateway, SAP Fiori|Fiori|Fiori Elements|SAP Fiori Elements, SAPUI5|SAP UI5|~^UI5|OpenUI5, SAP BTP|SAP Business Technology Platform|Business Technology Platform|SAP Cloud Platform|SCP, SAP Business Application Studio|Business Application Studio|SAP BAS, SAP Web IDE, IDoc|IDocs|~^IDOC, BAPI|BAPIs, BADI|BAdI|BADIs, RFC|~^RFCs, ALE, ~^EDI, User Exits|User Exit|Customer Exits|Customer Exit, Enhancement Framework|Enhancement Spots|Implicit Enhancements|Explicit Enhancements|Implicit/Explicit Enhancements, SmartForms|Smart Forms|Smart forms|Smartform, SAPscript|SAP Script|SAP Scripts|Sap Scripts, Adobe Forms|Adobe Form|Interactive Adobe Forms, ALV|ALV Reports|ALV Report, BDC|Batch Data Communication, LSMW, Module Pool|Module Pool Programming|Module pool Programming|Dialog Programming|Screen Programming, Function Modules|Function Module, Data Dictionary|ABAP Dictionary|~^DDIC, Runtime Analysis|SAT, SQL Trace|ST05, Code Inspector, SAP Workflow, SAP BRF+|BRF+|BRFplus|BRF Plus, SAP Basis|~^Basis, SAP Security, SAP NetWeaver|NetWeaver, SAP Solution Manager|SolMan, SAP PI/PO|PI/PO|SAP PI|SAP PO|SAP XI|SAP Process Integration, SAP CPI|SAP Cloud Platform Integration|SAP Integration Suite|Cloud Platform Integration|~^CPI|iFlow|iFlows, SAP BODS|BODS|SAP Data Services, SAP BW|SAP BW/4HANA|BW/4HANA, SAP Analytics Cloud|~^SAC, SAP Migration Cockpit|LTMC, SAP HANA Studio, Behavior Definitions|Behaviour Definitions|Behavior Definition, Clean ABAP|Clean Code
SAP_FUNC: SAP|SAP ERP, SAP FICO|~^FICO|SAP FI/CO|SAP FI CO, SAP FI|SAP Finance, SAP CO|SAP Controlling, SAP MM|SAP Materials Management, SAP SD|SAP Sales and Distribution, SAP PP|SAP Production Planning, SAP QM, SAP PM|SAP Plant Maintenance, SAP WM, SAP EWM|Extended Warehouse Management, SAP HCM|SAP HR, SAP SuccessFactors|SuccessFactors, SAP Ariba|Ariba, SAP CRM, SAP SRM, SAP SCM, SAP APO, SAP IBP, SAP TM, SAP PS|SAP Project System, SAP GRC, SAP MDG|Master Data Governance, SAP C4C|C4C|SAP Cloud for Customer|Cloud for Customer|SAP C4HANA|C4HANA|SAP C/4HANA|C/4HANA, SAP Sales Cloud|SAP Sales Cloud V1|SAP Sales Cloud V2|SAP Sales Cloud Version 2|Sales Cloud V2|Sales Cloud V1, SAP Service Cloud|SAP Service Cloud V1|SAP Service Cloud V2|SAP Service Cloud Version 2|Service Cloud V2|Service Cloud V1, SAP Marketing Cloud, SAP Commerce Cloud|SAP Commerce|SAP Hybris|Hybris, SAP CPQ|SAP Configure Price Quote|Callidus CPQ, SAP CX, KUT|Key User Tools|KUT Rule Editor, SAP Cloud Applications Studio|Cloud Applications Studio|SAP SDK|PDI, SAP Business One|SAP B1|~^B1, SAP Activate|SAP Activate Methodology, SAP Concur|Concur, SAP Signavio|Signavio, SAP Datasphere, ~Fit-Gap Analysis|Fit Gap Analysis|Fit/Gap Analysis, ~Cutover Planning|Cutover, ~Hypercare|Hyper Care, Business Blueprint|~^Blueprinting, Order to Cash|O2C|OTC, Procure to Pay|P2P, Record to Report|R2R, ~MRP, ~Variant Configuration, ~Intercompany
SALESFORCE: Salesforce|SFDC|Salesforce.com|Salesforce CRM|Force.com|SalesForce, Lightning Web Components|LWC|Lightning Web Component|Lightning Web Component Development, Aura Components|Aura Framework|Aura Component|~^Aura, Visualforce|Visual Force|Visualforce Pages, Salesforce Lightning|Lightning Experience|~^Lightning, Lightning App Builder|App Builder, Salesforce Flows|Flow Builder|Salesforce Flow|Screen Flows|~^Flows, Process Builder, Workflow Rules|~Workflows, ~Approval Processes|Approval Process, Validation Rules, Apex Triggers|Apex Trigger|~^Triggers|~^Trigger, Batch Apex|Apex Batch|Batch Classes|Batch Apex Classes, Schedulable Apex|Scheduled Apex|Schedulable Classes, Queueable Apex, Test Classes|Apex Test Classes, Sales Cloud|Salesforce Sales Cloud, Service Cloud|Salesforce Service Cloud, Marketing Cloud|Salesforce Marketing Cloud, Experience Cloud|Community Cloud, Financial Services Cloud|FSC|Financial Service Cloud, Health Cloud, Field Service Lightning|FSL|Salesforce Field Service, Salesforce CPQ|SFDC CPQ|Steelbrick CPQ, Pardot|Account Engagement, Salesforce Admin|Salesforce Administration|Salesforce Administrator, Salesforce DX|SFDX, OmniStudio|Omni Studio|OmniScripts|OmniScript|Omniscripts|DataRaptors|DataRaptor|FlexCards|FlexCard|Integration Procedures|Vlocity, Copado, Gearset, Change Sets|Changesets|Change Set, Data Loader|Apex Data Loader|Dataloader|Data loader|Salesforce Data Loader, Data Import Wizard, Salesforce Workbench|Workbench, SLDS|Lightning Design System, Einstein Analytics|Tableau CRM|CRM Analytics, Conga|Conga Composer, DocuSign, Nintex|Nintex Drawloop|Nintex Draw loop, Jasdoc|JasDoc, Genesys|Genesys Cloud, Sharing Rules|~Sharing Settings, Salesforce Security Model|~Role Hierarchy|~Profiles and Permission Sets, Salesforce Integration|Salesforce Integrations, ~Page Layouts, ~Record Types, ~Custom Objects
SFCC: Salesforce Commerce Cloud|SFCC|SalesForce Commerce Cloud|B2C Commerce Cloud|Salesforce B2C Commerce|B2C Commerce|Demandware|~Commerce Cloud, SFRA|Storefront Reference Architecture, SiteGenesis|Site Genesis|Sitegenesis, PWA Kit|PWA Kit (Headless Commerce)|Composable Storefront, OCAPI|Open Commerce API, SCAPI|Salesforce Commerce API, SFCC Business Manager|~Business Manager|~^BM, Page Designer, Cartridges|~^Cartridge|Custom Cartridges, Managed Runtime
DYNAMICS: Dynamics 365|D365|MS Dynamics|Microsoft Dynamics|MS Dynamics 365|Microsoft Dynamics 365|MS Dynamics365|Dynamics365|Dynamics CRM|MS CRM|Microsoft Dynamics CRM|Microsoft Dynamics ERP, Dynamics 365 CE|D365 CE|Dynamics 365 Customer Engagement|Dynamics 365 CE (Sales and Field Service), Dynamics 365 Field Service|D365 Field Service, Dynamics 365 Sales|D365 Sales, Dynamics 365 Finance and Operations|D365 F&O|D365 FO|Dynamics AX, Business Central|Dynamics NAV|Navision, Power Apps|PowerApps|Power App|Canvas Apps|Model-Driven Apps, Power Automate|Microsoft Flow|MS Flow, Power Platform|Microsoft Power Platform, Power Pages, Dataverse|Common Data Service, Plugins|~Plugin Development
ORACLE_APPS: Oracle Fusion|Oracle Fusion Applications|Fusion, Oracle EBS|Oracle E-Business Suite|Oracle Apps, Oracle Cloud ERP|Oracle ERP Cloud|Oracle ERP, Oracle HCM, Oracle SCM, Oracle APEX, OBIEE, Oracle SOA, PeopleSoft, JD Edwards|JDE, Siebel, Hyperion, NetSuite|Oracle NetSuite, Workday|Workday HCM, Workday Financials
ITSM: ServiceNow ITSM|ServiceNow Developer, ServiceNow ITOM, Remedy, Zendesk, Freshdesk, Freshservice
PM_METHOD: Agile|Agile Methodology|Agile Methodologies|Agile Scrum, Scrum, Kanban, SAFe|Scaled Agile, Waterfall, ~Lean, Six Sigma|Lean Six Sigma, Design Thinking, PMP, PRINCE2, ~CSM|Certified Scrum Master, SDLC|Software Development Life Cycle, Sprint Planning, ~Backlog Grooming|Backlog Refinement, User Stories|User Story, Object Oriented Programming|OOP|OOPS|OOPs|OOP's|OOAD, Design Patterns, ~Data Structures|DSA|Data Structures and Algorithms, ~Algorithms, System Design|Solution Architecture|Software Architecture, ~Multithreading, ~Distributed Systems, Performance Tuning|Performance Optimization|Performance Optimisation|~Code Optimization, ~Code Review|Code Reviews|Peer Code Reviews, Technical Documentation, ~Debugging, ~Version Control, API Design|API Development, ~Integration|~Integrations|~System Integration
BUSINESS: Project Management, Program Management, Product Management, Stakeholder Management, Business Analysis|Business Analyst, Requirement Gathering|Requirements Gathering|Requirements Analysis|Requirement Analysis, Functional Specifications|Functional Specification|FSD|Functional Design Document|Functional Requirement Document|FRD, Technical Specifications|Technical Specification|TSD, BRD|Business Requirement Document, Process Mapping|~Business Process Mapping, Gap Analysis, Change Management, ~Budgeting, Financial Analysis, Financial Reporting, Accounting, ~Taxation, ~^GST, ~^TDS, IFRS, ~Payroll, Recruitment|Talent Acquisition|Recruiting|IT Recruitment, ~Sourcing|Candidate Sourcing, Boolean Search, ~Onboarding, ~Employee Engagement, HRIS, ~Performance Management, ~Negotiation, ~Client Management|Client Handling, ~Account Management, ~Sales, B2B Sales, Business Development, Lead Generation, ~CRM, ~Pre-Sales|Presales, Digital Marketing, SEO, SEM, Google Ads, Social Media Marketing, Content Marketing, Email Marketing, Market Research, Supply Chain Management, ~Logistics, ~Inventory Management, ~Customer Service|Customer Support, ~Customer Success, ~Team Leadership|Team Management|People Management, ~Leadership, ~Mentoring|Coaching, ~Training|~Train-the-Trainer, ~Problem Solving|Problem-Solving, ~Analytical Skills, ~Communication Skills, ~Presentation Skills, ~Real Estate|Real Estate Domain, ~Lead Management, ~Case Management, ~Data Migration, ~Data Cleansing, ~Master Data Management|MDM, ~Reporting|~Reports and Dashboards|~Dashboards, ~KPI Reporting|KPIs|KPI, ~Forecasting, ~Asset Management, ~Mortgage
"""

_FAMILY_LABEL = {"SAP_TECH": "SAP technical (ABAP/Fiori/BTP)", "SAP_FUNC": "SAP functional", "SALESFORCE": "Salesforce CRM", "SFCC": "Salesforce Commerce Cloud",
                 "DEVOPS": "DevOps", "CLOUD_AWS": "AWS", "CLOUD_AZURE": "Azure", "CLOUD_GCP": "GCP", "FRONTEND": "Frontend", "BACKEND_JAVA": "Java backend",
                 "BACKEND_JS": "Node.js backend", "BACKEND_PY": "Python backend", "DOTNET": ".NET", "DATA": "Data / BI", "ML_AI": "AI / ML", "TESTING": "QA / Testing",
                 "DYNAMICS": "Microsoft Dynamics / Power Platform", "ORACLE_APPS": "Oracle apps / Workday", "DATABASE": "Databases", "MOBILE": "Mobile",
                 "SECURITY": "Security", "INFRA": "Infrastructure", "ITSM": "ITSM", "WEB": "APIs & integration", "LANG": "Programming languages",
                 "VCS_TOOLS": "Tools", "PM_METHOD": "Methods", "BUSINESS": "Business"}
_GENERIC_FAMILIES = {"VCS_TOOLS", "PM_METHOD", "BUSINESS", "LANG", "WEB", "DATABASE"}


def _build_taxonomy():
    alias, canon_family, ambiguous, case_sens, spaced = {}, {}, set(), {}, {}
    for line in _SKILL_DATA.strip().split("\n"):
        fam, _, body = line.partition(":")
        fam = fam.strip()
        for chunk in body.split(","):
            names = [n.strip() for n in chunk.split("|") if n.strip()]
            if not names:
                continue
            canon = names[0].lstrip("~^")
            canon_family.setdefault(canon, fam)
            for raw in names:
                flags = re.match(r"^[~^]*", raw).group(0)
                name = raw[len(flags):]
                key = _k(name)
                if not key:
                    continue
                if key in alias:
                    if alias[key] == canon and " " in name:
                        spaced[key] = True            # 'Java Script' may be written with a space
                    continue                          # first definition wins (incl. its ~ / ^ flags)
                alias[key] = canon
                spaced[key] = spaced.get(key, False) or (" " in name)
                if "~" in flags:
                    ambiguous.add(key)
                if "^" in flags:
                    case_sens.setdefault(key, set()).add(name)
    return alias, canon_family, ambiguous, case_sens, spaced


_ALIAS, _FAMILY, _AMBIG, _CASE, _SPACED = _build_taxonomy()

# child skill -> skills it proves (full credit when a JD asks for the parent)
_IMPLIES = {
    "Spring Boot": ["Spring", "Java"], "Spring MVC": ["Spring", "Java"], "Spring": ["Java"], "Hibernate": ["Java", "JPA"], "JPA": ["Java"],
    "React": ["JavaScript"], "Angular": ["JavaScript", "TypeScript"], "Vue.js": ["JavaScript"], "Next.js": ["React", "JavaScript"], "Node.js": ["JavaScript"],
    "TypeScript": ["JavaScript"], "jQuery": ["JavaScript"], "SASS": ["CSS"], "Bootstrap": ["CSS"], "Tailwind CSS": ["CSS"],
    "Django": ["Python"], "Flask": ["Python"], "FastAPI": ["Python"], "Pandas": ["Python"], "NumPy": ["Python"], "PySpark": ["Python", "Apache Spark"],
    "PyTorch": ["Python", "Machine Learning", "Deep Learning"], "TensorFlow": ["Python", "Machine Learning", "Deep Learning"], "scikit-learn": ["Python", "Machine Learning"],
    "EKS": ["Kubernetes", "AWS"], "AKS": ["Kubernetes", "Azure"], "GKE": ["Kubernetes", "GCP"], "OpenShift": ["Kubernetes"], "Helm": ["Kubernetes"],
    "Kubernetes": ["Containerization"], "Docker": ["Containerization"], "Docker Compose": ["Docker"],
    "EC2": ["AWS"], "S3": ["AWS"], "AWS Lambda": ["AWS", "Serverless"], "IAM": ["AWS"], "VPC": ["AWS"], "CloudFormation": ["AWS", "Infrastructure as Code"],
    "Azure DevOps": ["Azure", "CI/CD"], "Azure Functions": ["Azure", "Serverless"], "Azure App Service": ["Azure"], "Azure SQL": ["Azure", "SQL"], "ARM Templates": ["Azure", "Infrastructure as Code"],
    "Terraform": ["Infrastructure as Code"], "Jenkins": ["CI/CD"], "GitHub Actions": ["CI/CD"], "GitLab CI": ["CI/CD"], "Spinnaker": ["CI/CD"], "ArgoCD": ["CI/CD"], "Azure Pipelines": ["CI/CD", "Azure DevOps"],
    "Ansible": ["Configuration Management"], "Prometheus": ["Monitoring"], "Grafana": ["Monitoring"], "Splunk": ["Monitoring"],
    "MySQL": ["SQL", "RDBMS"], "PostgreSQL": ["SQL", "RDBMS"], "SQL Server": ["SQL", "RDBMS"], "Oracle Database": ["SQL", "RDBMS"], "PL/SQL": ["SQL"], "T-SQL": ["SQL"],
    "MongoDB": ["NoSQL"], "Cosmos DB": ["NoSQL", "Azure"], "DynamoDB": ["NoSQL", "AWS"], "Cassandra": ["NoSQL"], "Redis": ["NoSQL"],
    "Scrum": ["Agile"], "Kanban": ["Agile"], "SAFe": ["Agile"],
    "SAP ABAP": ["ABAP", "SAP"], "ABAP OO": ["ABAP", "SAP ABAP"], "CDS Views": ["SAP HANA", "SAP ABAP"], "AMDP": ["SAP HANA", "SAP ABAP"], "SAP RAP": ["SAP ABAP", "OData", "CDS Views"],
    "SAP S/4HANA": ["SAP", "SAP HANA"], "SAP HANA": ["SAP"], "SAP ECC": ["SAP"], "SAP Fiori": ["SAP", "SAPUI5"], "SAPUI5": ["SAP", "JavaScript"], "SAP BTP": ["SAP"],
    "SAP CPI": ["SAP", "SAP BTP"], "SAP PI/PO": ["SAP"], "SmartForms": ["SAP ABAP"], "SAPscript": ["SAP ABAP"], "Adobe Forms": ["SAP ABAP"], "ALV": ["SAP ABAP"], "BDC": ["SAP ABAP"],
    "BAPI": ["SAP ABAP"], "BADI": ["SAP ABAP"], "User Exits": ["SAP ABAP"], "Module Pool": ["SAP ABAP"], "IDoc": ["SAP"], "OData": ["REST"],
    "SAP Sales Cloud": ["SAP C4C", "SAP"], "SAP Service Cloud": ["SAP C4C", "SAP"], "SAP C4C": ["SAP", "SAP CX"], "KUT": ["SAP C4C"], "SAP FICO": ["SAP"], "SAP MM": ["SAP"], "SAP SD": ["SAP"],
    "SAP PP": ["SAP"], "SAP CPQ": ["SAP"], "SAP Commerce Cloud": ["SAP"], "SAP Analytics Cloud": ["SAP"], "SAP Activate": ["SAP"],
    "Apex": ["Salesforce", "SOQL"], "Lightning Web Components": ["Salesforce", "JavaScript"], "Aura Components": ["Salesforce"], "Visualforce": ["Salesforce"], "SOQL": ["Salesforce"],
    "Sales Cloud": ["Salesforce"], "Service Cloud": ["Salesforce"], "Marketing Cloud": ["Salesforce"], "Experience Cloud": ["Salesforce"], "Financial Services Cloud": ["Salesforce"],
    "Salesforce CPQ": ["Salesforce"], "OmniStudio": ["Salesforce"], "Salesforce Flows": ["Salesforce"], "Process Builder": ["Salesforce"], "Apex Triggers": ["Apex", "Salesforce"],
    "Batch Apex": ["Apex", "Salesforce"], "Salesforce Admin": ["Salesforce"], "Copado": ["Salesforce", "CI/CD"],
    "SFRA": ["Salesforce Commerce Cloud"], "SiteGenesis": ["Salesforce Commerce Cloud"], "PWA Kit": ["Salesforce Commerce Cloud", "React"], "OCAPI": ["Salesforce Commerce Cloud"],
    "SCAPI": ["Salesforce Commerce Cloud"], "ISML": ["Salesforce Commerce Cloud"], "Page Designer": ["Salesforce Commerce Cloud"],
    "Dynamics 365 CE": ["Dynamics 365"], "Dynamics 365 Field Service": ["Dynamics 365"], "Dynamics 365 Sales": ["Dynamics 365"], "Power Apps": ["Power Platform"], "Power Automate": ["Power Platform"],
    "Power BI": ["Data Visualization"], "Tableau": ["Data Visualization"], "Selenium": ["Automation Testing"], "Cypress": ["Automation Testing"], "Playwright": ["Automation Testing"],
    "Appium": ["Mobile Testing", "Automation Testing"], "JMeter": ["Performance Testing"], "LoadRunner": ["Performance Testing"], "REST Assured": ["API Testing"], "Postman": ["API Testing"],
}
# skills that are close enough to give partial credit (0.5) and be shown as "related"
_RELATED = [("AWS", "Azure", "GCP"), ("EKS", "AKS", "GKE", "OpenShift"), ("Jenkins", "Azure DevOps", "GitHub Actions", "GitLab CI", "Bamboo", "TeamCity", "CircleCI", "Spinnaker", "ArgoCD"),
            ("Terraform", "CloudFormation", "ARM Templates", "Bicep", "Pulumi"), ("Ansible", "Puppet", "Chef"), ("Prometheus", "Datadog", "New Relic", "Dynatrace", "AppDynamics", "Splunk", "ELK Stack", "Azure Monitor"),
            ("React", "Angular", "Vue.js"), ("MySQL", "PostgreSQL", "SQL Server", "Oracle Database", "MariaDB"), ("MongoDB", "Cosmos DB", "DynamoDB", "Cassandra", "Couchbase"),
            ("Selenium", "Cypress", "Playwright", "Puppeteer"), ("TestNG", "JUnit", "PyTest"), ("Power BI", "Tableau", "Qlik Sense", "Looker", "QlikView"),
            ("Kafka", "RabbitMQ", "ActiveMQ", "Azure Service Bus", "SQS"), ("SAP CPI", "SAP PI/PO", "MuleSoft", "Dell Boomi", "TIBCO"), ("SAP Fiori", "SAPUI5"),
            ("Lightning Web Components", "Aura Components", "Visualforce"), ("Salesforce Flows", "Process Builder", "Workflow Rules"), ("Copado", "Gearset", "Change Sets"),
            ("SFRA", "SiteGenesis"), ("OCAPI", "SCAPI"), ("SAP Sales Cloud", "Sales Cloud", "Dynamics 365 Sales"), ("SAP Service Cloud", "Service Cloud"),
            ("SAP S/4HANA", "SAP ECC"), ("CDS Views", "AMDP"), ("SmartForms", "Adobe Forms", "SAPscript"), ("BADI", "User Exits", "Enhancement Framework"),
            ("Docker", "Podman"), ("Git", "SVN"), ("GitHub", "GitLab", "Bitbucket"), ("Jira", "Azure Boards"), ("Spring Boot", "Quarkus", "Micronaut"), ("Django", "Flask", "FastAPI"),
            ("Dynamics 365", "Salesforce"), ("Oracle Fusion", "SAP S/4HANA", "Dynamics 365 Finance and Operations")]
_REL = {}
for _grp in _RELATED:
    for _s in _grp:
        _REL.setdefault(_s, set()).update(x for x in _grp if x != _s)

_SKILLS_LABEL_RE = re.compile(r"(?i)\b(?:skills?|technolog(?:y|ies)|tools?|environment|tech(?:nical)?\s*stack|stack|platforms?|languages?|frameworks?|databases?|expertise|competenc(?:y|ies)|"
                              r"proficien(?:cy|t in)|scripting|devops|cloud|monitoring|api management|containeri[sz]ation|version control|methodolog(?:y|ies)|os|operating systems?)\s*[:\-–]")
_TOKEN_RE = re.compile(r"[A-Za-z0-9.#+][A-Za-z0-9+#./']*(?:&[A-Za-z0-9]+)*")
_STOP_LEAD = {"in", "of", "on", "at", "to", "and", "the", "a", "an", "for", "with", "by", "or", "as", "is", "be", "using", "via", "from", "into"}


_PROSE_START = re.compile(r"(?i)^\W*(?:ensure[sd]?|develop(?:ed|s)?|design(?:ed|s)?|work(?:ed|s)?|manag(?:ed|es)|implement(?:ed|s)?|creat(?:ed|es)|buil[dt]s?|led|lead|responsible|involved|"
                          r"perform(?:ed|s)?|participat(?:ed|es)|collaborat(?:ed|es)|handl(?:ed|es)|provid(?:ed|es)|conduct(?:ed|s)?|support(?:ed|s)?|analy[sz](?:ed|es)|configur(?:ed|es)|"
                          r"maintain(?:ed|s)?|coordinat(?:ed|es)|deliver(?:ed|s)?|prepar(?:ed|es)|gather(?:ed|s)?|enhanc(?:ed|es)|troubleshoot(?:ed|s)?|monitor(?:ed|s)?|automat(?:ed|es)|"
                          r"migrat(?:ed|es)|integrat(?:ed|es)|optimi[sz](?:ed|es)|resolv(?:ed|es)|review(?:ed|s)?|tested|test|write|wrote|writing|good|strong|excellent|having|have|has|"
                          r"experience[ds]?|proficient|knowledge|expertise|skilled|able|ability|oversee|oversaw|drive|drove|own(?:ed)?|defin(?:ed|e)|plan(?:ned)?|facilitat(?:ed|e)|"
                          r"mentor(?:ed)?|train(?:ed)?|document(?:ed)?|track(?:ed)?|identif(?:ied|y)|assist(?:ed)?|help(?:ed)?|execut(?:ed|e)|act(?:ed)?|serv(?:ed|e)|achiev(?:ed|e)|"
                          r"improv(?:ed|e)|reduc(?:ed|e)|increas(?:ed|e)|streamlin(?:ed|e)|establish(?:ed)?|architect(?:ed)?|engineer(?:ed)?|utili[sz](?:ed|e)|used|use|using|applied|apply)\b")


def _skill_context_lines(text, skill_spans=()):
    """Indices of lines that look like skill lists (comma lists, label lists, short bullets, skills sections)."""
    lines = text.split("\n")
    ok = set()
    in_span = set()
    for a, b in skill_spans:
        in_span.update(range(a, b))
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            continue
        seps = len(re.findall(r"[,;|/•]", s))
        words = len(s.split())
        items = [x for x in re.split(r"[,;|/•]", s) if x.strip()]
        short = sum(1 for x in items if len(x.split()) <= 4)
        prose = bool(s.endswith(".") and words > 10 or _PROSE_START.match(s) and words > 6)
        if i in in_span and not prose:
            ok.add(i)
        elif seps >= 2 and items and short / len(items) >= 0.7 and not prose:
            ok.add(i)
        elif _SKILLS_LABEL_RE.search(s[:60]):
            ok.add(i)
        elif words <= 5 and not s.endswith("."):
            ok.add(i)
        elif re.search(r"\(([^()]{2,80}[,/][^()]{2,80})\)", s):
            ok.add(i)
    return ok


def _expand_for_skills(text):
    """Rewrite shared-suffix phrases so each product is visible: 'SAP Sales & Service Cloud V2' -> 'SAP Sales Cloud V2, SAP Service Cloud V2'."""
    def repl(m):
        pre = m.group(1) or ""
        ver = m.group(2) or ""
        return f"{pre}Sales Cloud{ver}, {pre}Service Cloud{ver}"
    t = re.sub(r"\b(SAP\s+)?Sales\s*(?:&|and)\s*Service\s+Cloud(\s+V\d)?", repl, text, flags=re.I)
    t = re.sub(r"\b(SAP\s+)?Sales\s+Cloud\s+(?:&|and)\s+Service\s+Cloud", lambda m: f"{m.group(1) or ''}Sales Cloud, {m.group(1) or ''}Service Cloud", t, flags=re.I)
    t = re.sub(r"\bSAP\s+(S/4\s?HANA|ECC|B1)\s*,\s*(ECC|B1)\s*(?:,|&|and)\s*(CPQ)\b", r"SAP \1, SAP \2, SAP \3", t)
    t = re.sub(r"\b(V1)\s*&\s*(V2)\b", r"\1, \2", t)
    return t


def extract_skills(text, use_nlp=True, with_counts=False, skill_line_idx=None, _detail=False):
    """Canonical skills in the text, most important first. Ambiguous words (Go, R, Spring, Lean, Integration...)
    only count inside skill lists. `use_nlp` is accepted for backward compatibility (no model is needed)."""
    text = _expand_for_skills(_clean(text))
    lines = text.split("\n")
    ctx = skill_line_idx if skill_line_idx is not None else _skill_context_lines(text)
    found, first, where = {}, {}, {}
    toks = []                                          # (word, line, start, end) over the whole text
    for li, ln in enumerate(lines):
        for m in _TOKEN_RE.finditer(ln):
            w = m.group(0).rstrip(".'")
            if not w:
                continue
            if "/" in w and _k(w) not in _ALIAS and not re.fullmatch(r"[A-Za-z]/\d?[A-Za-z0-9]+", w):
                parts = [p for p in w.split("/") if p]
                if len(parts) > 1:
                    off = m.start()
                    for p in parts:
                        toks.append((p.rstrip(".'"), li, off, off + len(p)))
                        off += len(p) + 1
                    continue
            toks.append((w, li, m.start(), m.start() + len(w)))
    hits, pending = [], []                             # pending = ambiguous hits that need a neighbouring skill
    i = 0
    while i < len(toks):
        hit = None
        for n in (6, 5, 4, 3, 2, 1):
            if i + n > len(toks):
                continue
            seg = toks[i:i + n]
            if seg[-1][1] - seg[0][1] > 1:
                continue
            key = _k("".join(t[0] for t in seg))
            if key not in _ALIAS:
                continue
            cross = seg[-1][1] != seg[0][1]
            if cross and (key in _AMBIG or not _SPACED.get(key)):
                continue                              # only clear multi-word skills may wrap onto the next line
            li = seg[0][1]
            raw = lines[li][seg[0][2]:seg[-1][3]] if not cross else " ".join(t[0] for t in seg)
            if n > 1:
                if seg[0][0].lower() in _STOP_LEAD:
                    continue
                if not _SPACED.get(key) and (" " in raw or cross):
                    continue                          # 'in design' is not InDesign, 'I am' is not IAM
            if key in _CASE:
                variants = _CASE[key]
                if not any(re.sub(r"\s+", " ", raw) == v or raw.replace(" ", "") == v.replace(" ", "") for v in variants):
                    continue
            weak = key in _AMBIG or (len(key) <= 2 and key not in _CASE and not raw.isupper())
            if weak:
                ln_full = lines[li]
                a0, b0 = seg[0][2], seg[-1][3]
                if (a0 > 0 and ln_full[a0 - 1] == "-") or (b0 < len(ln_full) and ln_full[b0:b0 + 1] == "-"):
                    break                             # 'Go-Live' is not Go
                if raw.islower() and (len(ln_full) > 70 or ln_full.rstrip().endswith(":")):
                    break                             # lower-case word inside a sentence ('performance management, ensuring ...')
            hit = (n, _ALIAS[key], li, seg[0][2], seg[-1][3], weak and li not in ctx)
            break
        if hit:
            n, c, li, a, b, needs_neighbour = hit
            (pending if needs_neighbour else hits).append((c, li, a, b))
            i += n
        else:
            i += 1
    for c, li, a, b in pending:                        # 'Apex triggers, Flows, formulas' -> Flows counts (listed next to a real skill)
        ln = lines[li]
        for c2, l2, a2, b2 in hits:
            if l2 != li or c2 == c:
                continue
            gap = ln[b2:a] if b2 <= a else ln[b:a2]
            if len(gap) <= 6 and re.fullmatch(r"[\s,&/()]*(?:and|or)?[\s,&/()]*", gap):
                hits.append((c, li, a, b))
                break
    for c, li, a, b in sorted(hits, key=lambda h: (h[1], h[2])):
        found[c] = found.get(c, 0) + 1
        first.setdefault(c, (li, a))
        where.setdefault(c, set()).add(li)
    if re.search(r"(?i)\babap\s+on\s+hana\b", text) and "SAP HANA" not in found:
        found["SAP HANA"] = 1
        first.setdefault("SAP HANA", first.get("SAP ABAP", (0, 0)))
        where.setdefault("SAP HANA", set()).update(where.get("SAP ABAP", set()))
    # SAP Sales/Service Cloud resumes must not be tagged with Salesforce clouds
    if ("SAP C4C" in found or "SAP Sales Cloud" in found or "SAP Service Cloud" in found) and "Salesforce" not in found:
        for sf, sap in (("Sales Cloud", "SAP Sales Cloud"), ("Service Cloud", "SAP Service Cloud"), ("Marketing Cloud", "SAP Marketing Cloud")):
            if sf in found:
                found[sap] = found.get(sap, 0) + found.pop(sf)
                first.setdefault(sap, first.pop(sf))
                where.setdefault(sap, set()).update(where.pop(sf, set()))
    # Salesforce Commerce Cloud resumes: 'Salesforce Certified ... Commerce Cloud' is not Salesforce CRM
    if "Salesforce Commerce Cloud" in found and "Salesforce" in found and not ({"Apex", "Lightning Web Components", "Sales Cloud", "Service Cloud", "SOQL", "Visualforce"} & set(found)):
        found.pop("Salesforce")
        first.pop("Salesforce", None)
        where.pop("Salesforce", None)
    ranked = sorted(found, key=lambda c: (-found[c], first[c]))
    if _detail:
        return ranked, found, first, where
    return (ranked, found) if with_counts else ranked


# =====================================================================================
# 4. SECTIONS
# =====================================================================================
_SECTION_WORDS = [
    ("projects", r"projects?\s*(?:undertaken|summary|details|experience|handled|worked\s*on)?|key\s*projects|academic\s*projects|personal\s*projects|project\s*profile|assignments"),
    ("experience", r"(?:professional|work|working|employment|career|industry|relevant|corporate)?\s*(?:experience|history|employment|background)(?:\s*(?:summary|details|history))?|employment\s*history|work\s*history|career\s*history|experience|organizational\s*experience|professional\s*journey|job\s*responsibilities|key\s*responsibilities"),
    ("education", r"(?:educational|academic)\s*(?:qualifications?|credentials|background|details|profile)|education(?:al)?(?:\s*(?:qualifications?|details|background|&\s*certifications?))?|qualifications?|academics?|scholastic\s*profile"),
    ("skills", r"(?:technical|key|core|it|professional|functional|soft|primary|secondary|computer|software)?\s*(?:skills?|skill\s*set|skillset|competenc(?:y|ies)|expertise|proficienc(?:y|ies)|technolog(?:y|ies)|tools?(?:\s*(?:&|and)\s*technologies)?)(?:\s*(?:&|and)\s*(?:expertise|tools|technologies|abilities|competencies))?|areas?\s*of\s*expertise|technical\s*profile|tools\s*(?:&|and)\s*platforms|it\s*skills|skills\s*summary"),
    ("certs", r"(?:certifications?|certificates?|certificate\s*courses?|licen[cs]es?(?:\s*(?:&|and)\s*certifications?)?|trainings?(?:\s*(?:&|and)\s*certifications?)?|courses?|professional\s*development|(?:sap|salesforce|aws|azure|microsoft)\s*certifications?)"),
    ("summary", r"(?:professional|profile|career|executive|personal)?\s*(?:summary|profile|objective|overview)|about\s*me|career\s*objective|objective|introduction|professional\s*synopsis"),
    ("awards", r"(?:awards?|achievements?|accomplishments?|recognitions?|honou?rs?)(?:\s*(?:&|and|/)\s*(?:awards?|achievements?|recognitions?|honou?rs?|scholarships?))*"),
    ("personal", r"personal\s*(?:details|information|profile|data)|declaration|languages?(?:\s*known)?|hobbies|interests|references|strengths|extra[\s\-]*curricular(?:\s*activities)?|other\s*details|additional\s*information"),
    ("contact", r"contact(?:\s*(?:details|information|info|me))?"),
]
_SECTION_RES = [(n, re.compile(r"^(?:%s)$" % p, re.I)) for n, p in _SECTION_WORDS]
_INLINE_LABELS = re.compile(r"(?i)^(?:roles?\s*(?:and|&)\s*responsibilit(?:y|ies)|responsibilit(?:y|ies)|key\s*contributions?|project\s*(?:summary|description|details)|description|environment|technologies|duties|achievements?\s*at\s*\w+|key\s*result\s*areas?)\s*:?\s*$")


def _heading_of(line):
    s = line.strip()
    if not s or len(s) > 60:
        return None
    s = re.sub(r"^[#•*\-–=>\s\d.)]+", "", s)
    s = re.sub(r"[:\-–—=_*#|]+\s*$", "", s).strip()
    if not s or len(s.split()) > 6 or re.search(r"[@\d]{3,}", s):
        return None
    if _INLINE_LABELS.match(s) and not s.isupper():
        return None
    low = re.sub(r"\s+", " ", s.lower().replace("&", " & "))
    low = re.sub(r"\s+", " ", low).strip()
    for name, rx in _SECTION_RES:
        if rx.match(low):
            return name
    # ALL-CAPS short line ending with a section word ('DOCKER & CONTAINERIZATION EXPERIENCE', 'SAP CERTIFICATIONS')
    if s.isupper() and len(s.split()) <= 5:
        last = low.split()[-1]
        for name, kw in (("experience", "experience"), ("skills", "skills"), ("certs", "certifications"), ("education", "education"), ("projects", "projects"), ("awards", "awards")):
            if last == kw:
                return name if not (name == "experience" and re.search(r"(?i)project", s)) else "projects"
        if re.search(r"(?i)\b(?:competenc|expertise)", s):
            return "skills"
    return None


def _sections(lines):
    """Per-line section label + ordered list of (name, start, end) spans."""
    labels, cur = [], "header"
    spans, start = [], 0
    for i, ln in enumerate(lines):
        h = _heading_of(ln)
        if h:
            spans.append((cur, start, i))
            cur, start = h, i + 1
            labels.append("heading:" + h)
            continue
        m = re.match(r"^\s*(technical\s+skills|key\s+skills|skills|education|educational\s+qualifications?|qualifications?|certifications?)\s*[:\-–]\s*(\S.{2,})$", ln, re.I)
        if m:                                           # 'Education: B.Tech, JNTU, 2018' -> this line only
            w = m.group(1).lower()
            labels.append("skills" if "skill" in w else "certs" if "certif" in w else "education")
        else:
            labels.append(cur)
    spans.append((cur, start, len(lines)))
    return labels, [s for s in spans if s[2] > s[1]]


# =====================================================================================
# 5. DATES
# =====================================================================================
_MONTHS = {"jan": 0, "feb": 1, "mar": 2, "apr": 3, "may": 4, "jun": 5, "jul": 6, "aug": 7, "sep": 8, "oct": 9, "nov": 10, "dec": 11}
_MON = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_DAY = r"(?:\d{1,2}(?:st|nd|rd|th)?[\s,]+)"
_YEAR4 = r"(?:19[7-9]\d|20[0-4]\d)"
_DATE = (r"(?:(?:" + _DAY + r")?" + _MON + r"\.?[\s,'\-]*(?:" + _DAY + r")?'?\s*(?:" + _YEAR4 + r"|\d{2}(?!\d))"
         r"|(?:0?[1-9]|1[0-2])\s*[/.\-]\s*" + _YEAR4 + r"|" + _YEAR4 + r"\s*[/.\-]\s*(?:0?[1-9]|1[0-2])(?!\d)|" + _YEAR4 + r")")
_NOW = r"(?:present|current(?:ly)?|till\s*(?:date|now|today)|to\s*date|now|ongoing|today|continuing|running|date)"
_SEP = r"(?:\s*(?:-|–|—|~|to|till|until|through|thru)\s*)"
_RANGE_RE = re.compile(r"(?<![\w/])(" + _DATE + r")" + _SEP + r"(" + _DATE + r"|" + _NOW + r")(?![\w/])", re.I)
_SINCE_RE = re.compile(r"(?i)\b(?:since|from)\s+(" + _DATE + r")(?!\s*(?:-|–|—|to|till|until))\b")


def _month_index(s, today, is_end=False):
    s = s.strip().lower()
    cap = today.year * 12 + today.month - 1
    if re.fullmatch(_NOW, s, re.I):
        return cap, True
    m = re.search(r"(" + _MON + r")\.?[\s,'\-]*(?:" + _DAY + r")?'?\s*(" + _YEAR4 + r"|\d{2})\b", s, re.I)
    if m:
        mo = _MONTHS[m.group(1)[:3].lower()]
        y = int(m.group(2))
        if y < 100:
            y += 2000 if y <= (today.year % 100) + 1 else 1900
        return min(y * 12 + mo, cap), False
    m = re.search(r"(\d{1,2})\s*[/.\-]\s*(" + _YEAR4 + r")", s) or re.search(r"(" + _YEAR4 + r")\s*[/.\-]\s*(\d{1,2})", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        y, mo = (b, a) if a <= 12 else (a, b)
        return min(y * 12 + mo - 1, cap), False
    m = re.search(_YEAR4, s)
    y = int(m.group(0))
    return min(y * 12 + (11 if is_end else 0), cap), False


def _fmt_month(mi):
    return "%s %d" % (["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][mi % 12], mi // 12)


def _find_ranges(text, today):
    out = []
    for m in _RANGE_RE.finditer(text):
        try:
            a, _ = _month_index(m.group(1), today)
            b, now = _month_index(m.group(2), today, is_end=True)
        except (AttributeError, ValueError, KeyError):
            continue
        if b < a or b - a > 600 or a < 1970 * 12:
            continue
        out.append({"start": a, "end": b, "now": now, "pos": m.start(), "endpos": m.end(), "text": m.group(0)})
    for m in _SINCE_RE.finditer(text):
        if any(r["pos"] <= m.start() < r["endpos"] for r in out):
            continue
        try:
            a, _ = _month_index(m.group(1), today)
        except (AttributeError, ValueError, KeyError):
            continue
        cap = today.year * 12 + today.month - 1
        if re.search(r"(?i)\b(?:since|from)\b", m.group(0)) and re.search(r"(?i)(?:work|employ|join|associated|serv)", text[max(0, m.start() - 120):m.start()]):
            out.append({"start": a, "end": cap, "now": True, "pos": m.start(), "endpos": m.end(), "text": m.group(0)})
    return sorted(out, key=lambda r: r["pos"])


def _union_months(intervals):
    total, last = 0, -1
    for a, b in sorted(intervals):
        if b <= last:
            continue
        total += b - max(a, last)
        last = b
    return total


# =====================================================================================
# 6. CONTACT DETAILS
# =====================================================================================
_TLDS = "com org net edu gov info biz dev tech co in io ai us uk ca au de ae sg me sa qa om bh kw nz za fr nl".split()


def _emails(text):
    t = re.sub(r"(?i)\s*[\[(]\s*at\s*[\])]\s*", "@", text)
    t = re.sub(r"(?i)\s*[\[(]\s*dot\s*[\])]\s*", ".", t)
    t = re.sub(r"(?<=[A-Za-z0-9._%+\-])\s+@\s*(?=[A-Za-z0-9])|(?<=[A-Za-z0-9._%+\-])@\s+(?=[A-Za-z0-9])", "@", t)
    t = re.sub(r"(@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.c)\s+(om)\b", r"\1\2", t)          # 'gmail.c om'
    t = re.sub(r"(@[A-Za-z0-9\-]+)\s+(\.[A-Za-z]{2,})", r"\1\2", t)
    out = []
    for m in re.finditer(r"[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}", t):
        e = m.group(0).strip(".-_")
        local, dom = e.rsplit("@", 1)
        labels = dom.split(".")
        last = labels[-1].lower()
        if last not in _TLDS and len(last) > 3:
            fix = next((x for x in sorted(_TLDS, key=len, reverse=True) if last.startswith(x)), None)
            if fix:
                labels[-1] = fix
        e = (local + "@" + ".".join(labels)).lower()
        if e not in out:
            out.append(e)
    return out


_CC = {"971": "United Arab Emirates", "966": "Saudi Arabia", "974": "Qatar", "968": "Oman", "973": "Bahrain", "965": "Kuwait", "1": "USA", "44": "United Kingdom",
       "61": "Australia", "65": "Singapore", "49": "Germany", "353": "Ireland", "33": "France", "31": "Netherlands", "41": "Switzerland", "81": "Japan", "60": "Malaysia",
       "64": "New Zealand", "27": "South Africa", "254": "Kenya", "91": "India", "94": "Sri Lanka", "977": "Nepal", "880": "Bangladesh", "92": "Pakistan", "20": "Egypt"}


def _phones(text):
    """All plausible phone numbers, best first: (normalised, country_code)."""
    cands = []
    for m in re.finditer(r"(?<![\w/])(\+?\s?\(?\d{1,4}\)?[\s\-.]?)?(\(?\d[\d\s\-().]{7,16}\d)(?![\w/])", text):
        raw = (m.group(0) or "").strip()
        digits = re.sub(r"\D", "", raw)
        if re.search(r"(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}", raw) or re.fullmatch(r"(?:19|20)\d{6}", digits):
            continue
        ctx = text[max(0, m.start() - 25):m.start()].lower()
        if re.search(r"(?:id|pan|aadhaar|aadhar|passport|pin|zip|account|a/c|cin|gst)\s*[:#.\-]*\s*$", ctx):
            continue
        norm, cc = None, None
        if len(digits) == 10 and digits[0] in "6789" and not raw.startswith("+"):
            norm, cc = "+91 %s %s" % (digits[:5], digits[5:]), "91"
        elif len(digits) in (11, 12, 13) and (digits.startswith("91") and len(digits) == 12 or digits.startswith("091") or digits.startswith("0") and len(digits) == 11) and digits[-10] in "6789":
            d = digits[-10:]
            norm, cc = "+91 %s %s" % (d[:5], d[5:]), "91"
        elif raw.startswith("+") or raw.startswith("00"):
            d = digits[2:] if raw.startswith("00") else digits
            code = next((c for c in sorted(_CC, key=len, reverse=True) if d.startswith(c)), None)
            if code and 7 <= len(d) - len(code) <= 11:
                norm, cc = "+%s %s" % (code, d[len(code):]), code
        elif len(digits) == 10 and re.fullmatch(r"\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]\d{4}", raw):
            norm, cc = raw, "1"
        if not norm:
            continue
        score = 0
        if re.search(r"(?:mobile|phone|mob|cell|contact|tel|ph|m)\s*(?:no\.?|number|#)?\s*[:.\-]?\s*$", ctx):
            score += 3
        if m.start() < 800:
            score += 2
        cands.append((score, -m.start(), norm, cc))
    cands.sort(reverse=True)
    seen, out = set(), []
    for _, _, n, cc in cands:
        if n not in seen:
            seen.add(n)
            out.append((n, cc))
    return out


_CITIES = ("Bangalore|Bengaluru,Hyderabad,Secunderabad,Pune,Pimpri-Chinchwad|Pimpri|Chinchwad,Chennai,Mumbai,Navi Mumbai,Thane,Kalyan,Vasai,Panvel,New Delhi,Delhi,Noida,Greater Noida,"
           "Gurgaon|Gurugram,Ghaziabad,Faridabad,Kolkata|Calcutta,Howrah,Ahmedabad,Gandhinagar,Surat,Vadodara|Baroda,Rajkot,Jaipur,Udaipur,Jodhpur,Kota,Ajmer,Lucknow,Kanpur,Agra,Varanasi,"
           "Prayagraj|Allahabad,Meerut,Nagpur,Nashik,Aurangabad,Solapur,Kolhapur,Sangli,Satara,Indore,Bhopal,Gwalior,Jabalpur,Patna,Ranchi,Jamshedpur,Dhanbad,Bhubaneswar,Cuttack,"
           "Visakhapatnam|Vizag,Vijayawada,Guntur,Nellore,Tirupati,Kurnool,Kakinada,Rajahmundry,Warangal,Karimnagar,Huzurabad,Nizamabad,Coimbatore,Madurai,Trichy|Tiruchirappalli,"
           "Salem,Erode,Tiruppur,Vellore,Tirunelveli,Thanjavur,Karaikudi,Hosur,Pondicherry|Puducherry,Kochi|Cochin,Ernakulam,Trivandrum|Thiruvananthapuram,Kozhikode|Calicut,Thrissur,Kannur,"
           "Kollam,Palakkad,Mysore|Mysuru,Mangalore|Mangaluru,Hubli|Hubballi,Dharwad,Belgaum|Belagavi,Davangere,Gulbarga|Kalaburagi,Shimoga|Shivamogga,Udupi,Manipal,Chandigarh,Mohali,"
           "Panchkula,Ludhiana,Amritsar,Jalandhar,Patiala,Dehradun,Haridwar,Shimla,Jammu,Srinagar,Goa|Panaji,Margao,Raipur,Bhilai,Guwahati,Shillong,Siliguri,Durgapur,Asansol,Jalgaon,"
           "Amravati,Akola,Latur,Nanded,Ahmednagar,Bareilly,Aligarh,Gorakhpur,Jhansi,Ujjain,Bhavnagar,Jamnagar,Anand,Vapi,Valsad,Karnal,Panipat,Sonipat,Rohtak,Hisar,Bilaspur,Kanpur,"
           "Dubai,Abu Dhabi,Sharjah,Ajman,Al Ain,Ras Al Khaimah,Fujairah,Umm Al Quwain,Doha,Riyadh,Jeddah,Dammam,Al Khobar|Khobar,Muscat,Manama,Kuwait City,"
           "London,Manchester,Birmingham,Leeds,Glasgow,Edinburgh,Dublin,New York,New Jersey,San Francisco,San Jose,Seattle,Austin,Chicago,Boston,Dallas,Houston,Atlanta,Charlotte,Phoenix,"
           "Denver,Toronto,Vancouver,Montreal,Calgary,Sydney,Melbourne,Brisbane,Perth,Auckland,Singapore,Kuala Lumpur,Berlin,Munich,Frankfurt,Amsterdam,Paris,Zurich,Stockholm,"
           "Copenhagen,Tokyo,Hong Kong,Colombo,Kathmandu,Dhaka").split(",")
_CITY_CANON = {}
for _c in _CITIES:
    _names = _c.split("|")
    for _n in _names:
        _CITY_CANON[_n.lower()] = _names[0]
_CITY_RE = re.compile(r"\b(" + "|".join(sorted((re.escape(n) for n in _CITY_CANON), key=len, reverse=True)) + r")\b", re.I)
_STATES = ("Andhra Pradesh,Telangana,Karnataka,Tamil Nadu,Kerala,Maharashtra,Gujarat,Rajasthan,Madhya Pradesh,Uttar Pradesh,Uttarakhand,Bihar,Jharkhand,Odisha,Orissa,West Bengal,"
           "Assam,Punjab,Haryana,Himachal Pradesh,Jammu and Kashmir,Chhattisgarh,Goa,Delhi NCR,NCR").split(",")
_COUNTRIES = ("India,United Arab Emirates,UAE,Saudi Arabia,KSA,Qatar,Oman,Bahrain,Kuwait,United States,USA,United Kingdom,UK,Canada,Australia,Germany,Singapore,Ireland,"
              "Netherlands,France,Switzerland,Malaysia,New Zealand,Denmark,Sweden,Philippines,Sri Lanka,Nepal").split(",")
_STATE_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, _STATES), key=len, reverse=True)) + r")\b", re.I)
_COUNTRY_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, _COUNTRIES), key=len, reverse=True)) + r")\b")


def _city_in(s):
    m = _CITY_RE.search(s or "")
    if not m:
        return ""
    raw = m.group(1)
    if raw.isupper() and len(raw) > 4 and raw.lower() not in ("delhi", "pune", "goa"):
        pass
    return _CITY_CANON[raw.lower()]


# =====================================================================================
# 7. ROLES, COMPANIES
# =====================================================================================
_ROLE_WORDS = (r"engineer|developer|consultant|architect|analyst|manager|lead|administrator|admin|tester|designer|specialist|executive|associate|intern|director|head|"
               r"scientist|recruiter|officer|coordinator|programmer|technician|accountant|trainee|expert|owner|president|vp|cto|ceo|cfo|coo|sme|principal|advisor|adviser|"
               r"strategist|merchandiser|controller|auditor|supervisor|representative|partner|founder|co-founder|freelancer|instructor|trainer|lecturer|professor|teacher|"
               r"writer|editor|marketer|planner|operator|agent|buyer|assistant|clerk|secretary|receptionist|nurse|doctor|pharmacist|chemist|researcher|fellow|apprentice|"
               r"steward|evangelist|champion|owner|practitioner|expert|devops|sre|dba|qa|ba|pm|scrum\s*master|product\s*owner|delivery\s*manager|team\s*lead|tech\s*lead")
_ROLE_RE = re.compile(r"\b(?:" + _ROLE_WORDS + r")s?\b", re.I)
_ROLE_CONT = {"technology", "technologies", "l1", "l2", "l3", "i", "ii", "iii", "iv", "1", "2", "3", "(ce)", "ce", "grade", "level"}
_COMP_SUFFIX = re.compile(r"\b(?:pvt|private|ltd|limited|inc|incorporated|llc|llp|plc|corp|corporation|co\.|company|gmbh|ag|bv|sa|technologies|technology\s+services|"
                          r"solutions|systems|services|consulting|consultancy|consultants|software|softwares|infotech|infosystems|infoservices|info\s*tech|labs|bank|group|"
                          r"industries|enterprises|global|softech|soft\s*tech|technosoft|ventures|holdings|properties|associates|partners|networks|digital|analytics|"
                          r"healthcare|pharma|pharmaceuticals|motors|telecom|communications|media|retail|international|india|equipments?|construction|manufacturing|"
                          r"logistics|insurance|finance|financial|capital|university|institute|hospital|foundation|studios?|commerce|tech)\b", re.I)
_KNOWN_COMPANIES = [
    "Tata Consultancy Services", "TCS", "Infosys", "Wipro", "HCL Technologies", "HCLTech", "HCL", "Tech Mahindra", "Cognizant", "Accenture", "Capgemini", "IBM", "Deloitte", "EY",
    "Ernst & Young", "KPMG", "PwC", "PricewaterhouseCoopers", "LTIMindtree", "LTI Mindtree", "Mindtree", "L&T Infotech", "LTI", "Larsen & Toubro", "L&T Technology Services", "LTTS",
    "Mphasis", "Hexaware", "Cyient", "Publicis Sapient", "Sapient", "NTT Data", "NTT DATA", "Brillio", "Persistent Systems", "Persistent", "Zensar", "Birlasoft", "Virtusa", "UST Global",
    "UST", "Coforge", "NIIT Technologies", "NIIT", "Oracle", "SAP Labs", "Microsoft", "Amazon", "AWS", "Google", "Meta", "Facebook", "Apple", "Genpact", "Mastek", "Sonata Software",
    "KPIT", "Happiest Minds", "Tata Elxsi", "DXC Technology", "DXC", "Atos", "Unisys", "CGI", "Synechron", "Nagarro", "EPAM", "GlobalLogic", "Ness", "Infogain", "Quess", "Randstad",
    "3i Infotech", "Enzigma", "Saffron", "InTWO", "Levtech", "Cloudway", "Wipro Digital", "Hitachi", "Fujitsu", "NEC", "Siemens", "Bosch", "Honeywell", "Philips", "GE", "Dell",
    "HP", "HPE", "Cisco", "VMware", "Salesforce", "ServiceNow", "Adobe", "Intel", "Qualcomm", "Nvidia", "Samsung", "LG", "Walmart", "Target", "JP Morgan", "JPMorgan", "Morgan Stanley",
    "Goldman Sachs", "Barclays", "HSBC", "Citi", "Citibank", "Deutsche Bank", "Wells Fargo", "American Express", "Standard Chartered", "UBS", "Credit Suisse", "BNY Mellon",
    "State Street", "Fidelity", "Optum", "UnitedHealth", "Mu Sigma", "Fractal", "Tiger Analytics", "LatentView", "ZS Associates", "Thoughtworks", "Altimetrik", "Ciklum",
    "Movate", "Firstsource", "Sutherland", "Concentrix", "Teleperformance", "Conduent", "Mindteck", "Sasken", "Quest Global", "Tata Technologies", "Mahindra", "Reliance",
    "Jio", "Airtel", "Vodafone", "Flipkart", "Paytm", "Swiggy", "Zomato", "Ola", "Uber", "Myntra", "PhonePe", "Razorpay", "Freshworks", "Zoho", "Infoedge", "Naukri",
    "Ducon", "DAMAC", "Al Ghurair", "Deyaar", "Emaar", "Abbott", "Dynapac", "PS International", "OSF Commerce", "SMC Square", "PFSCommerce", "Searchnscore", "AKGS Infotech",
]
_KNOWN_RE = re.compile(r"\b(" + "|".join(sorted(map(re.escape, _KNOWN_COMPANIES), key=len, reverse=True)) + r")\b", re.I)
_NOT_COMPANY = re.compile(r"(?i)^(?:present|current|currently|till\s*date|working|worked|experience|company|organi[sz]ation|employer|client|project|projects|role|roles|"
                          r"responsibilities|summary|duration|period|tenure|from|to|since|india|remote|onsite|offshore|full[\s\-]?time|part[\s\-]?time|contract|permanent|"
                          r"business use only|confidential|internal|page \d+|resume|curriculum vitae|cv|professional experience|work experience)\W*$")


def _is_location(s):
    s2 = re.sub(r"[()]", "", s).strip(" ,.")
    if not s2:
        return False
    parts = [p.strip() for p in re.split(r"[,/]", s2) if p.strip()]
    return all(_CITY_RE.fullmatch(p) or _STATE_RE.fullmatch(p) or _COUNTRY_RE.fullmatch(p) or p.upper() in ("IN", "KA", "TN", "AP", "TS", "MH", "UP", "WB", "NCR") for p in parts)


def _is_roleish(s):
    return bool(_ROLE_RE.search(s)) and len(s.split()) <= 9


def _is_companyish(s):
    return bool(_COMP_SUFFIX.search(s) or _KNOWN_RE.search(s))


def _split_role_company(text):
    """Split an undelimited header like 'SENIOR TECH LEAD WIPRO LTD.' into (role, company)."""
    words = text.split()
    km = _KNOWN_RE.search(text)
    if km and km.start() > 0:
        before = text[:km.start()].strip(" ,-|")
        if _is_roleish(before):
            return before, text[km.start():].strip()
    last = None
    for i, w in enumerate(words):
        if _ROLE_RE.fullmatch(re.sub(r"[^A-Za-z\-]", "", w)) or _ROLE_RE.fullmatch(w.strip(",.()")):
            last = i
    if last is None or last == len(words) - 1:
        return (text, "") if _is_roleish(text) else ("", text)
    j = last + 1
    while j < len(words) - 1 and words[j].strip(",.").lower() in _ROLE_CONT:
        j += 1
    role, comp = " ".join(words[:j]), " ".join(words[j:])
    if len(comp.split()) >= 1 and (_is_companyish(comp) or comp.isupper() or comp[:1].isupper()):
        return role, comp
    return text, ""


def _clean_piece(s):
    s = re.sub(r"\s+", " ", s or "").strip(" \t|,;:-–—•*()[]")
    s = re.sub(r"(?i)^(?:\d+\s*[).:]\s*)", "", s)
    s = re.sub(r"(?i)^(?:company|organi[sz]ation|employer|client|role|designation|position|title|project)\s*(?:name)?\s*[:\-–]\s*", "", s)
    s = re.sub(r"(?i)\s*\b(?:from|since|during|between|till|until|to)\s*$", "", s).strip(" ,.-–")
    s = re.sub(r"([a-z])(Properties|Technologies|Solutions|Services|Systems|Consulting|Industries|Group|Infotech|Software)\b", r"\1 \2", s)
    s = re.sub(r"\(\s*$", "", s).strip()
    if s.count("(") > s.count(")"):
        s += ")"
    return s


# =====================================================================================
# 8. NAME
# =====================================================================================
_NAME_STOP = set(("resume curriculum vitae cv bio data biodata profile summary objective contact address email e-mail phone mobile page career personal details information "
                  "technical skills skill experience education work history professional declaration references having around over about years year yrs months total overall "
                  "with seeking looking worked working currently possess strong good excellent hands name date birth dob gender male female nationality indian married single "
                  "father mother husband linkedin github portfolio website india uae dubai bangalore bengaluru hyderabad pune chennai mumbai delhi noida gurgaon kolkata "
                  "senior junior lead principal staff associate trainee fresher certified salesforce sap oracle microsoft azure aws google java python developer engineer "
                  "consultant analyst manager architect tester designer administrator specialist executive intern director head officer team cloud data devops frontend "
                  "backend fullstack full stack software hardware network web mobile application applications project projects key core competencies expertise areas "
                  "the and of for in at to a an my our is are be on as by from experienced motivated dedicated passionate skilled results driven dynamic "
                  "detail oriented hardworking aspiring accomplished overview highlights synopsis goal goals snapshot achievements about me abilities "
                  "strengths hiring urgent client clients dear sir madam present current programming scripting processing performance improve generation "
                  "retrieval augmented platform modernization using fabric technologies solutions services flows validation rules vault veeva "
                  "certification certifications training internship role roles responsibilities languages known hobbies interests declaration "
                  "objective reference contact phone mobile tel cell telephone summary profile email id mail linkedin github "
                  "worked working organization company employer database databases sql oracle python java testing tools engineering engineer "
                  "telecommunication inventory procurement purchase lists records source curriculm curriculam vita vitae resume ltd pvt limited "
                  "solutions digital tech softech technologies joiner immediate operations telugu hindi kannada tamil english marathi malayalam "
                  "bengali gujarati punjabi urdu creative aspirants specialises specializes specialist concepts university college school institute "
                  "link links trailhead bring-up exposure area skill skills set expertise competencies key classic git bitbucket within demand").split())

_COMMON_WORDS = set((
    "abilities ability about accelerate accelerated accelerating acceptance access accomplishments account accounts accuracy accurate accurately "
    "achieve achieved achieving across actionable actions activation active activities activity adaptations adding additional addressed "
    "addressing adherence adhering admin administration admins adoption advanced after against agency agents agile agreed agreement agreements "
    "alerts align aligned aligning alignment allocation also alternative always analysis analysts analytical analytics analyze analyzed ansible "
    "apex application applications apply appointments approval approved approx approximately apps architects architectural architecture areas "
    "arise arrangements articles asset assets assigned assigning assignment assignments assisted assisting associated audit authored authoring "
    "authorisation authorisations authorized automate automated automating automation automotive availability available avoided avoiding award "
    "awards backbone backend background backlog balancer balancers bandwidth banking based baseline bases basics basketball batch been before "
    "best between blockers blueprint blueprinting boarded booking books boosting both bottlenecks brand brands bridge bridged brief browser "
    "budget build building builds built business businesses cache calls campaigns capabilities capture capturing cards care career cart "
    "cartridge cartridges case cases cash catalogs cause ceremonies certificate certificates certification certifications certified challenging "
    "change changes channel channels characteristics chart charts check checklist checkout checks choosing claims clarifications classes clean "
    "cleansing clearings client clients closely cloud cloudbased clusters code codes coding collaborating collaboration collaborative collected "
    "combined combines commands commerce commercial commitment committed committee communication company compatibility compatible complaints "
    "complete completed completeness completion complex compliance component components comprehensive concurrent conducted conducting config "
    "configurable configuration configurations configure configured configuring conglomerate conjunction connected connectivity consistency "
    "consistently constraints constructed construction consultancy consultant consultants consuming consumption contacts container "
    "containerization containerized containing contains content continue continuity continuous contracts contribute contributing control "
    "controllers conventions conversion converted coordinated core corporate cost course coverage covering create created creating creation "
    "creativity criteria critical cross current custom customer customers customisation customization customizations customize customized "
    "customizing cutover cycle cycles daily dashboard dashboards data database date days deactivating deactivation dealer debugging decision "
    "decisionmaking decisions decreased deed defect defects deleting deliver deliverables delivered delivering delivery departments dependencies "
    "dependency deployed deploying deployment deployments design designed designers designing designs detailed details detection determination "
    "determinations developed developer developers developing development developments diagrams dialog different direct directional directly "
    "disaster discovery discussed display distinct distribution distributions diverse divisions document documentation documented documenting "
    "documents doing domains done downtime drafted drive driven driving during dynamic early ecommerce effective effectively efficiency "
    "efficient efficiently element elicit eliminated email emails employee employees enable enabled enabling enforcement engagements engineer "
    "enhance enhanced enhancement enhancements enhancing ensure ensured ensuring entered enterprise entry environment environments equipping "
    "errors escalated establishing estimated event events every evolving exchange exec execute executed executing execution executive existing "
    "exits expectations experience experienced experiences expert expertise expiries explicit export expose exposing exposure extending "
    "extensions external facilitated facing failover failures fast feature features feedback fetch field fields figures filed files finance "
    "financial financing fine finical firm first fixes flexibility flow flowcharts flows focus focusing folders follow followed force "
    "forecasting form format forms formulas foundation four framework frameworks freezing friendly from front frontend full fully function "
    "functional functionalities functionality future gaps gateways gather gathered gathering generate generating generation getting gift giving "
    "global goal goals good governance government graphics grasp grow growth guaranteed guidance guided guidelines handle handled handling "
    "handover hands hardening hardworking have health healthy help helped helping hierarchies hierarchy high highly historical holders hours "
    "house hyper hypercare identify identifying image images immediately impact impediments implement implementation implementations implemented "
    "implementing implicit import improve improved improvement improvements improving incident incidents including increase increasing "
    "individual industry inform information informed infrastructure ingress initiatives innovation innovative input inputs insight insights "
    "inspect insurance integrate integrated integrating integration integrations integrity interaction interactions interactive interface "
    "interfaces intermittent internal interpersonal intervention into introduction investment investments invoice involves involving issue "
    "issues items jobs join junior keep keeping kernel keys kinds knowledge kube label landscape language large largest launch layer layers "
    "layout layouts lead leaders leadership leading leads learned learner lease leasing legacy lending less lessons level leveraged leveraging "
    "library lifecycle like line list lists live load loader loading loan logging logic login logo logs looking loop loss machines made maintain "
    "maintained maintaining maintenance making manage managed management managing manipulation manual mapping maps market marketing mashups "
    "master match matched material materials mechanisms media meet meeting meetings members mentored merge message methodologies methodology "
    "methods meticulously metrics microservices middleware migrating migration migrations minimal minimized ministry mirror misconfigurations "
    "mobile model modeling modified module modules monitor monitoring monolith monthly motivated movement multi multinational multiple "
    "multiregion name naming nationwide native navigation need needs network networking newer night notifications number object objectives "
    "objects observability obtain obtained occur occurrence offs offshore ongoing onsite open operational operations operators opportunities "
    "opportunity optimal optimised optimising optimization optimizations optimize optimized optimizing option orchestrated orchestration order "
    "orders ordinated ordinating organisation organisational organization organizational organizations oriented other others outputs outstanding "
    "over overall overrides oversight packages packaging page pages parallel part participated participating particular particularly parties "
    "partner party passionate patches patching pathbased payload payment payments peer perform performance performed performing permanent "
    "permission permissions persistent personal personalized personally personas pharmacy phase phases pick pipeline pipelines planning plans "
    "platform player pleasing policies policy pool portfolios position post practices precise prepared preparing presence presenter primarily "
    "printing prior priorities proactive proactively problem problems procedures process processes processing product production productivity "
    "products professional professionally profiles program programming programs progress progression progressive project projects promote "
    "promotion promotions promptly proper properties property protocols prototypes provide provided providing provisioning proxies proxy pull "
    "puram purchase purposes push qualification qualities quality quantitative quarterly queries query queue queues quick quotations quote "
    "quotes raised range rates readability ready real receipts received record recovery recurring redesign reduce reduced reducing reduction "
    "refine region regional regression regular related relations relationship release releases reliability reliable removing rent replacing "
    "replication report reported reporting reports repository represent representative reps reputed request requests required requirement "
    "requirements requisitions research resident residents resistance resolution resolve resolved resolving resource resources response "
    "responsive responsiveness restoration restricted restricting result resulted resulting results retail retrieval retrospectives reusable "
    "revenue reviewed reviews right robust role roles roll rollback rollout rollouts root routine routing rules runtime sales salesforce "
    "salesman same satisfaction satisfied save scalable scaling scanning scenarios schedule scheduled scheduling school scope scoped scoping "
    "scores screen screens script scripting scripts seamless search secondary secret secrets section sector secure security self sell sending "
    "senior sensitive sent served server service services sessions sets setting setup several sharing sheet showing side sign signature signed "
    "significantly signoff single site sites size skilled skills smooth social software solution solutions solving source sources specialization "
    "specific specifications sprint stabilise stability stable stack stage stages stakeholders stand standard standardisation standardise "
    "standardising standardized standards start state status steering steps storage storefront storefronts stories strategies strategy "
    "streamline streamlined streamlining street strengthening strict strong structure structured structures submitted successful successfully "
    "such sufficient suites supervising suppliers support supported supporting surveys switch sync synchronisation synchronised syntax system "
    "systems table tables tabs tailored tailoring take target targeted task tasks team teams teamwork tech technical techniques technologies "
    "technology templates tenant territory test tested testing tests that their them then third thorough those through throughout ticket tickets "
    "time timeline timelines timely timeouts times titles tools tournament traceability track tracking traditional traffic trained training "
    "transactional transactions transfer transferring transfers transformation transformations transition transitions translate translating "
    "translation transportation travel trends trigger triggers troubleshooting truly trust tuned tuning type types unavailability under "
    "understand understanding unfreezing uninterrupted unit units universal unlocking unmanaged upcoming update updates updating upgrade upload "
    "uploads uptime usability usable used user users using usual utility utilize utilized validate validating validation validations value "
    "variety various vendors verified verifying version virtual visibility visualize visually volume volumes vulnerability waiver walkthroughs "
    "warranty wavier website websites weekly weeks well were when where whether which while will windows winner wireframes with within without "
    "work workarounds worked workflow workflows working workshops workstreams would write writing years zero zone "
).split())
_NAME_STOP |= set("location business support job jobs recruitment recruiter sr jr care program automation following higher secondary results order management driven gmail yahoo hotmail outlook rediffmail email".split())
_GLUED = ("experience", "technical", "skills", "career", "summary", "profile", "objective", "education", "curriculum", "resume", "contact")


def _name_tokens(s):
    s = re.sub(r"(?i)^(?:mr|mrs|ms|miss|dr|prof|shri|smt|sri|kum|er)\.?\s+", "", s.strip())
    s = re.sub(r"[,|•·:;]+.*$", "", s).strip()
    toks = [t.strip(".-'") for t in s.split()]
    toks = [t for t in toks if t]
    for i, t in enumerate(toks):
        if i >= 1 and (t.lower() in _NAME_STOP or re.search(r"\d", t)):
            return toks[:i]
    return toks


def _valid_name(toks):
    if not 1 <= len(toks) <= 4:
        return False
    if sum(len(t) for t in toks) < 3:
        return False
    for t in toks:
        if not re.fullmatch(r"[A-Za-z][A-Za-z'\-]*\.?|[A-Za-z]", t):
            return False
        if len(t.rstrip(".")) == 1:
            continue                                    # initials ('Siddarth A', 'V. Aishwarya')
        tl = t.lower().rstrip(".")
        if any(part in _NAME_STOP or part in _COMMON_WORDS for part in tl.split("-") if part):
            return False                                # 'Results-driven', 'Business', 'Automation'
        if len(tl) > 8 and any(g in tl and g != tl for g in _GLUED):
            return False                                # 'Experiencetechnical', 'Skillscareer'
        if t.lower() in _NAME_STOP or _CITY_RE.fullmatch(t) or _k(t) in _ALIAS and len(t) >= 3 and _k(t) not in ("ray", "rust", "swift", "flask", "spring", "chef", "lean", "dash", "ruby", "julia", "sage", "basis", "unity", "jade"):
            return False
    caps = [t for t in toks if len(t) > 1]
    if not caps:
        return False
    if caps[0][0].islower() and not all(t.islower() for t in caps):
        return False                                    # 'having Around' is not a name; 'Rajasekhar chandrala' is
    if _KNOWN_RE.fullmatch(" ".join(toks)):
        return False
    return True


def _title_name(toks):
    out = []
    for t in toks:
        if len(t) == 1:
            out.append(t.upper())
        elif t.isupper() or t.islower():
            out.append(t[0].upper() + t[1:].lower())
        else:
            out.append(t)
    return out


def _filename_name(filename):
    """Name hints from the upload's file name: 'Naukri_GovindArjunSuryawanshi5y_5m.pdf' -> (['Govind','Arjun','Suryawanshi'], 5y5m)."""
    if not filename:
        return [], None, ""
    base = os.path.splitext(os.path.basename(filename))[0]
    base = re.sub(r"^[0-9a-f]{8}-", "", base)
    exp = None
    m = re.search(r"(?i)(\d{1,2})y[_\s\-]?(\d{1,2})m", base)
    if m:
        exp = int(m.group(1)) * 12 + int(m.group(2))
    nk = re.match(r"(?i)^naukri[_\-\s]*([A-Za-z]+?)(?:\d|\(|$)", base)
    raw = nk.group(1) if nk else ""
    if not raw:
        parts = re.split(r"[_\-\s.]+", base)
        keep = []
        generic = {"resume", "cv", "update", "updated", "final", "latest", "new", "profile", "naukri", "copy", "doc", "docx", "pdf", "v1", "v2", "v3", "draft", "my",
                   "functional", "technical", "techno", "senior", "junior", "lead", "fresher", "experienced", "exp", "years", "yrs", "uae", "india", "dubai", "usa", "uk",
                   "cx", "crm", "erp", "it", "hr", "qa", "ba", "pm", "dev", "ops", "fullstack", "frontend", "backend", "support", "admin"}
        for p in parts:
            if not p or re.search(r"\d", p) or p.lower() in generic:
                break
            if _k(p) in _ALIAS or _ROLE_RE.fullmatch(p) or p.lower() in _NAME_STOP:
                break
            keep.append(p)
        raw = " ".join(keep[:3])
    toks = re.findall(r"[A-Z][a-z]+|[A-Z]+(?![a-z])|[a-z]+", raw) if raw and not raw.isupper() and " " not in raw else raw.split()
    return [t for t in toks if t], exp, raw


def _pick_name(lines, labels, text, filename, emails, linkedin_slug):
    fn_toks, _, fn_raw = _filename_name(filename)
    is_portal = bool(filename and re.match(r"(?i)^(?:[0-9a-f]{8}-)?naukri", os.path.basename(filename)))
    fn_key = _norm(fn_raw)
    cands = []                                         # (score, tokens, source)
    top = [i for i, ln in enumerate(lines[:60]) if ln.strip()]
    contact_idx = [i for i, ln in enumerate(lines[:80]) if re.search(r"@|\+?\d[\d\s\-]{8,}\d", ln)]
    near = set()
    for ci in contact_idx[:3]:
        near.update(range(max(0, ci - 4), ci + 1))
    for rank, i in enumerate(top[:40]):
        ln = lines[i].strip()
        if not ln or labels[i].startswith("heading"):
            continue
        m = re.match(r"(?i)^\s*(?:full\s*)?name\s*[:\-]\s*(.+)$", ln)
        variants = []
        if m:
            variants.append((m.group(1), 40))
        if re.fullmatch(r"(?:[A-Za-z]\s){2,}[A-Za-z](?:\s{2,}(?:[A-Za-z]\s){1,}[A-Za-z])*", ln):   # 'R A S H M I T H A'
            variants.append((" ".join(w.replace(" ", "") for w in re.split(r"\s{2,}", ln)), 25))
        variants.append((ln, 0))
        # name followed by a role on the same line: 'GOVIND SURYAWANSHI SAP ABAP Consultant on HANA'
        words = ln.split()
        if len(words) > 2:
            for cut in (2, 3):
                if cut >= len(words):
                    break
                head = " ".join(words[:cut])
                rest = " ".join(words[cut:])
                if _is_roleish(rest) or _k(words[cut]) in _ALIAS:
                    variants.append((head, 5))
                    break
        # vertical names: 'Dhareppa\nMahadev\nKumbar'
        if len(words) == 1 and i + 1 < len(lines):
            seq = [ln]
            j = i + 1
            while j < len(lines) and len(seq) < 4 and len(lines[j].split()) == 1 and lines[j].strip():
                seq.append(lines[j].strip())
                j += 1
            if len(seq) >= 2:
                variants.append((" ".join(seq), 10))
        for v, bonus in variants:
            toks = _name_tokens(v)
            if not _valid_name(toks):
                continue
            score = bonus + max(0, 20 - rank * 2) + (8 if i in near else 0)
            score += 6 if len(toks) >= 2 else 0
            if v.isupper() or all(t[:1].isupper() for t in toks):
                score += 3
            if fn_key and _norm("".join(toks)) and (_norm("".join(toks)) in fn_key or fn_key in _norm("".join(toks))):
                score += 30
            elif fn_toks and set(t.lower() for t in toks) & set(t.lower() for t in fn_toks if len(t) > 1):
                score += 15
            for e in emails[:1]:
                loc = re.sub(r"[^a-z]", "", e.split("@")[0])
                if any(len(t) >= 3 and t.lower() in loc for t in toks):
                    score += 8
            cands.append((score, toks, "line"))
    # portal file names glue the name together ('DHAREPPAMAHADEVKUMBAR', 'RajapriyaA'): find the same letters as words in the text
    if fn_key and len(fn_key) >= 6:
        words = re.findall(r"[A-Za-z][A-Za-z'\-]*", text[:5000])
        for n in (4, 3, 2):
            hit = None
            for i in range(len(words) - n + 1):
                seg = words[i:i + n]
                cat = _norm("".join(seg))
                if cat == fn_key or (len(seg[-1]) > 1 and _norm("".join(seg[:-1])) + seg[-1][0].lower() == fn_key):
                    if _valid_name(seg):
                        hit = seg
                        break
            if hit:
                cands.append((90, hit, "filename-match"))
                break
    best = max(cands, key=lambda c: c[0]) if cands else None
    notes = []
    _pick_name.last_score = best[0] if best else 0
    toks = list(best[1]) if best and best[0] >= 15 else []
    if not toks and fn_toks and _valid_name(fn_toks) and len(fn_toks) >= 2:
        toks, notes = list(fn_toks), ["name taken from the file name"]
    if not toks and emails:
        parts = [p for p in re.split(r"[._\-+\d]+", emails[0].split("@")[0]) if len(p) > 1]
        if parts and _valid_name(parts[:3]):
            toks, notes = parts[:3], ["name derived from e-mail address - please verify"]
    if not toks:
        return [], ["name not found"]
    toks = _title_name(toks)
    low = [t.lower().rstrip(".") for t in toks]
    # the file name often has the full name in the right order ('RasiPatnala', 'GovindArjunSuryawanshi')
    if fn_toks and len(fn_toks) >= 2 and all(len(t) > 1 for t in fn_toks):
        fl = [t.lower() for t in fn_toks]
        if is_portal and set(low) <= set(fl) and len(fl) <= 4:
            toks = _title_name(fn_toks)
        elif len(low) >= 2 and set(fl) == set(low):
            toks = _title_name(fn_toks)
    # single name + LinkedIn slug 'rashmi-bandam' -> surname 'Bandam'
    if len(toks) == 1 and linkedin_slug:
        sl = [p for p in re.split(r"[\-_.]+", linkedin_slug.lower()) if p.isalpha() and len(p) > 1]
        if len(sl) >= 2 and len(sl[0]) >= 4 and toks[0].lower().startswith(sl[0]) and sl[1] != toks[0].lower():
            toks = toks + [sl[1].title()]
            notes.append("surname taken from LinkedIn URL - please verify")
    return toks, notes


# =====================================================================================
# 9. WORK EXPERIENCE
# =====================================================================================
_SENTENCE_JOB = re.compile(r"(?i)\b(?:worked|working|work|employed|serving|served|associated|currently\s+working)\s+(?:as\s+(?:an?\s+)?(?P<role>[A-Za-z][\w /&.+#\-]{2,60}?)\s+)?"
                           r"(?:at|with|in|for)\s+(?P<comp>[A-Z0-9][\w .,&()'\-]{2,80}?)(?:\s*,\s*(?P<loc>[A-Za-z .]{3,30}))?\s+(?:from|since|during|between)\b")


def _header_like(s):
    s = s.strip()
    if not s or s.startswith("•") or len(s) > 110:
        return False
    if re.search(r"@|https?://|www\.", s):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z&.'\-]*", s)
    if not words:
        return False
    if s.endswith(".") and not re.search(r"(?i)\b(?:ltd|inc|pvt|co|corp|llc)\.$", s) and len(words) > 4:
        return False
    caps = sum(1 for w in words if w[0].isupper() or w.lower() in _SMALL)
    return s.isupper() or caps / len(words) >= 0.6 or bool(re.search(r"\s[|–—]\s|^\s*(?:company|organi[sz]ation|employer|client|role|designation|position)\s*:", s, re.I))


_PROJECT_MARK = re.compile(r"(?i)^[\s•]*(?:project\s*(?:#?\s*\d+|name|title)?\s*[:\-–#]|project\s*#|client\s*[:\-]|\d+\s*[).]\s*client\s*[:\-]|end\s+to\s+end|implementation\s+for)")


def _parse_block(block_lines, same_line_rest):
    """Return dict(company, role, location, labelled, project) from the lines that describe one job."""
    info = {"company": "", "role": "", "location": "", "project": False, "client": "", "client_label": False}
    texts = [same_line_rest] + block_lines if same_line_rest else list(block_lines)
    for t in texts:
        lab = re.match(r"(?i)^\s*(?:\d+\s*[).]\s*)?(company|organi[sz]ation|employer|client|role|designation|position|title|location|project(?:\s*(?:#?\s*\d+|name|title))?)\s*[:\-–#]\s*(.*)$", t)
        if lab:
            key, val = lab.group(1).lower(), _clean_piece(lab.group(2))
            val = re.sub(r"\(\s*$", "", val).strip()
            if key in ("company", "organisation", "organization", "employer") and val:
                info["company"] = info["company"] or val
            elif key == "client" and val:
                info["client"] = info["client"] or val
                info["client_label"] = True
            elif key in ("role", "designation", "position", "title") and val:
                info["role"] = info["role"] or val
            elif key == "location":
                info["location"] = info["location"] or _city_in(val) or val
            elif key.startswith("project"):
                info["project"] = True
    if _PROJECT_MARK.search(" ".join(texts[:3])) or any(re.match(r"(?i)^\s*project\b", t) for t in texts):
        info["project"] = True
    joined = " ".join(t for t in texts if t)
    sm = _SENTENCE_JOB.search(joined + " from")
    if sm and not info["company"]:
        info["company"] = _clean_piece(sm.group("comp"))
        if sm.group("role"):
            info["role"] = info["role"] or _smart_title(_clean_piece(sm.group("role")).title() if sm.group("role").islower() else _clean_piece(sm.group("role")))
        if sm.group("loc") and _city_in(sm.group("loc")):
            info["location"] = _city_in(sm.group("loc"))
        return info
    if info["company"] and info["role"]:
        return info
    pieces = []
    for t in texts:
        if not t or re.match(r"(?i)^\s*(?:\d+\s*[).]\s*)?(?:company|organi[sz]ation|employer|client|role|designation|position|title|location|project|duration|period|tenure|environment)\b\s*[:\-–#]", t):
            continue
        t = re.sub(r"\[[^\]]*\]|\(\s*\)", " ", t)
        for p in re.split(r"\s*\|\s*|\s+[-–—]\s+|\s*[–—]\s*|(?<=[a-z0-9)])-(?=[A-Z0-9])|\s{3,}|\t|,\s+(?=[A-Z])|\s+@\s+|\s+at\s+(?=[A-Z])", t):
            p = _clean_piece(p)
            if p and not _NOT_COMPANY.match(p) and not re.fullmatch(r"[\d\s/.\-]+|\d+\s*(?:years?|months?|yrs?)(?:\s*\d+\s*months?)?", p, re.I):
                pieces.append(p)
    roles = [p for p in pieces if _is_roleish(p) and not (_is_companyish(p) and not _ROLE_RE.search(p.split()[-1]))]
    locs = [p for p in pieces if _is_location(p)]
    comps = [p for p in pieces if p not in roles and p not in locs and (_is_companyish(p) or p.isupper() or p[:1].isupper())]
    if not roles and not comps and pieces:
        r, c = _split_role_company(pieces[0])
        roles, comps = ([r] if r else []), ([c] if c else [])
    if roles and not comps:
        for r in roles:
            rr, cc = _split_role_company(r)
            if cc and (_is_companyish(cc) or cc.isupper()):
                roles, comps = [rr], [cc]
                break
    if comps and not roles:
        for c in comps:
            rr, cc = _split_role_company(c)
            if rr and cc:
                roles, comps = [rr], [cc]
                break
    info["role"] = info["role"] or (roles[0] if roles else "")
    if not info["company"]:
        info["company"] = comps[0] if comps else ""
        if len(comps) > 1 and not _is_companyish(comps[0]) and _is_companyish(comps[1]):
            info["company"] = comps[1]
    if locs and not info["location"]:
        info["location"] = _city_in(locs[0]) or locs[0]
    if info["client_label"] and not info["company"]:
        info["project"] = True                        # 'Client: X (dates)' with no employer -> a client engagement
    if info["client"] and _norm(info["client"]) == _norm(info["company"]):
        info["client"] = ""
    return info


def _work_entries(lines, labels, today, name_line_idx=()):
    text = "\n".join(lines)
    starts, pos = [], 0
    for ln in lines:
        starts.append(pos)
        pos += len(ln) + 1

    def line_of(p):
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= p:
                lo = mid
            else:
                hi = mid - 1
        return lo

    raw_entries = []
    for r in _find_ranges(text, today):
        li = line_of(r["pos"])
        sec = labels[li]
        if sec in ("education", "certs", "awards", "personal") or sec.startswith("heading"):
            continue
        line = lines[li]
        if re.search(r"(?i)\b(?:b\.?\s?tech|b\.?e\b|m\.?\s?tech|bachelor|master|mba|mca|bca|b\.?sc|m\.?sc|12th|10th|ssc|hsc|cgpa|gpa|percentage|graduat|school|college|university)\b", line) and sec != "experience":
            continue
        a, b = r["pos"] - starts[li], r["endpos"] - starts[li]
        rest = (line[:a] + " " + line[b:]).strip()
        rest = re.sub(r"(?i)\b(?:duration|period|tenure|dates?|from)\s*[:\-–]?\s*$|^\s*(?:duration|period|tenure|dates?)\s*[:\-–]\s*", "", rest).strip(" ()[]|,-–—:")
        if rest and not _SENTENCE_JOB.search(rest + " from") and (len(rest) > 110 or (_PROSE_START.match(rest) and len(rest.split()) > 6) or (rest.endswith(".") and len(rest.split()) > 8)):
            rest = ""                                     # a description sentence glued to the date (PyPDF2 text)
        above, j = [], li - 1
        while j >= 0 and len(above) < 4:
            s = lines[j].strip()
            if not s:
                if above:
                    break
                j -= 1
                continue
            if labels[j].startswith("heading") or _RANGE_RE.search(s) or j in name_line_idx:
                break
            if re.match(r"(?i)^\s*(?:role|designation|client|project|organi[sz]ation|company|employer|environment|position)\b.{0,3}[:\-–#]", s):
                above.insert(0, s)
                j -= 1
                continue
            s2 = s.lstrip("• ").strip()
            if not _header_like(s2) or (s.startswith("•") and (len(s2) > 90 or not (_is_roleish(s2) or _is_companyish(s2)))):
                break
            above.insert(0, s2)
            j -= 1
        below, j = [], li + 1
        while j < len(lines) and len(below) < 3:
            s = lines[j].strip()
            if not s or _RANGE_RE.search(s) or labels[j].startswith("heading"):
                break
            if re.match(r"(?i)^\s*(?:role|designation|client|organi[sz]ation|company|employer|position|location)\b\s*[:\-–]", s):
                below.append(s)
                j += 1
                continue
            if _header_like(s) and (_is_roleish(s) or (not rest and not above and _is_companyish(s))) and not re.match(r"(?i)^\s*(?:roles?\s*(?:&|and)\s*responsibilit|responsibilit|project|environment|technologies)", s):
                below.append(s)
                j += 1
                continue
            break
        # labelled project blocks: 'Duration:' line with Role/Client/Project lines a few lines above
        if re.match(r"(?i)^\s*(?:duration|period|tenure)\s*[:\-–]", line) and len(above) < 5:
            k = li - 1
            while k >= 0 and k >= li - 6 and lines[k].strip() and not _RANGE_RE.search(lines[k]):
                if lines[k].strip() not in above:
                    above.insert(0, lines[k].strip())
                k -= 1
        info = _parse_block(above + below, rest)
        raw_entries.append({"start": r["start"], "end": r["end"], "now": r["now"], "line": li, "first_line": li - len(above), "last_line": li + len(below),
                            "company": info["company"], "role": info["role"], "location": info["location"], "project": info["project"], "client": info["client"],
                            "orphan": not (info["company"] or info["role"] or info["client"]), "section": labels[li]})
    # undated job headers ('Salesforce Developer-Enzigma Solutions') + dates printed elsewhere -> pair in order
    orphans = [e for e in raw_entries if e["orphan"]]
    if orphans:
        used = set()
        for e in raw_entries:
            used.update(range(e["first_line"], e["last_line"] + 1))
        heads = []
        for i, ln in enumerate(lines):
            if labels[i] != "experience" or i in used or i in name_line_idx:
                continue
            s = ln.strip()
            if not s or s.startswith("•") or not _header_like(s) or len(s) > 90:
                continue
            info = _parse_block([], s)
            if info["role"] and info["company"] and not info["project"]:
                heads.append((i, info))
        if heads and len(orphans) >= len(heads):
            ordered = sorted(orphans, key=lambda e: (-e["end"], -e["start"]))[:len(heads)]
            for (i, info), e in zip(heads, ordered):
                e.update(company=info["company"], role=info["role"], location=info["location"], orphan=False, first_line=i, line=i, last_line=i)
    # de-duplicate (merged table cells, repeated headers)
    uniq = []
    for e in raw_entries:
        dup = next((u for u in uniq if u["start"] == e["start"] and u["end"] == e["end"] and (_norm(u["company"]) == _norm(e["company"]) or not e["company"] or not u["company"])), None)
        if dup:
            for f in ("company", "role", "location", "client"):
                dup[f] = dup[f] or e[f]
            dup["project"] = dup["project"] and e["project"]
            continue
        uniq.append(e)
    employers = [e for e in uniq if not e["orphan"] and not e["project"] and e["company"]]
    projects = [e for e in uniq if e["project"]]
    if employers:
        chosen = employers
    elif projects:
        chosen = projects
        for e in chosen:
            e["company"] = e["company"] or e["client"]
    else:
        chosen = [e for e in uniq if not e["orphan"]] or uniq
    # descriptions: lines after each header until the next entry's header
    chosen.sort(key=lambda e: e["line"])
    bounds = sorted(set(e["first_line"] for e in uniq))
    for e in chosen:
        nxt = next((b for b in bounds if b > e["last_line"]), len(lines))
        desc = []
        for j in range(e["last_line"] + 1, nxt):
            if labels[j].startswith("heading"):
                break
            s = lines[j].strip(" •")
            if s:
                desc.append(s)
        e["description"] = re.sub(r"\s+", " ", " ".join(desc))[:900]
    chosen.sort(key=lambda e: (-e["end"], -e["start"]))
    out = []
    for e in chosen:
        comp = _smart_title(e["company"])
        comp = re.sub(r"\s+\(\s*\)$", "", comp)
        role = _smart_title(e["role"])
        out.append({"company": comp, "role": role, "start_date": _fmt_month(e["start"]), "end_date": "Present" if e["now"] else _fmt_month(e["end"]),
                    "duration": "%s - %s" % (_fmt_month(e["start"]), "Present" if e["now"] else _fmt_month(e["end"])), "location": e["location"],
                    "description": e.get("description", ""), "client": _smart_title(e["client"]) if e["client"] and e["client"] != e["company"] else "",
                    "_iv": (e["start"], e["end"]), "_now": e["now"]})
    return out, [e for e in uniq if e["project"] and e not in chosen]


# =====================================================================================
# 10. EDUCATION, CERTIFICATIONS, PROJECTS
# =====================================================================================
_DEGREE_RE = re.compile(r"(?i)(?<![A-Za-z])(b\.?\s?tech\.?|m\.?\s?tech\.?|b\.?\s?e\.?(?=[\s,(|\-–/]|$)|m\.?\s?e\.?(?=[\s,(|\-–]|$)|b\.?\s?sc\.?|m\.?\s?sc\.?|b\.?\s?com\.?|m\.?\s?com\.?|"
                        r"b\.?\s?c\.?\s?a\.?|m\.?\s?c\.?\s?a\.?|b\.?\s?b\.?\s?a\.?|m\.?\s?b\.?\s?a\.?|pgdm|pgpm|pgdba|pgdca|pg\s?diploma|post\s*graduate\s*diploma|b\.?\s?a\.?(?=[\s,(]|$)|"
                        r"m\.?\s?a\.?(?=[\s,(]|$)|ph\.?\s?d|bachelor(?:'?s)?(?:\s+(?:of|in)\s+[A-Za-z&. ]{2,40})?|master(?:'?s)?(?:\s+(?:of|in)\s+[A-Za-z&. ]{2,40})?|"
                        r"diploma(?:\s+in\s+[A-Za-z&. ]{2,40})?|b\.?\s?pharm|m\.?\s?pharm|mbbs|b\.?\s?arch|llb|ll\.?m|ca\b|icwa|cma\b|intermediate(?:\s+education)?|higher\s+secondary|"
                        r"senior\s+secondary|hsc|ssc|sslc|12th|10th|xii|class\s+(?:x|xii))")
_INST_RE = re.compile(r"(?i)\b(university|college|institute|institution|school|academy|vidyalaya|vidyapeeth|polytechnic|board|iit|nit|iiit|bits|vtu|jntu|jntuh|jntuk|kits|vit|srm|"
                      r"amity|manipal|anna|osmania|mumbai university|pune university|delhi university|kl university|ibs|iim|xlri|nmims|symbiosis|campus)\b")
_DEGREE_LEVEL = [("phd", 5), ("ph.d", 5), ("doctor", 5), ("master", 4), ("m.tech", 4), ("mtech", 4), ("m tech", 4), ("mba", 4), ("mca", 4), ("m.sc", 4), ("msc", 4), ("m.com", 4),
                 ("pgdm", 4), ("pgpm", 4), ("m.e", 4), ("post graduate", 4), ("bachelor", 3), ("b.tech", 3), ("btech", 3), ("b tech", 3), ("b.e", 3), ("be,", 3), ("bca", 3),
                 ("b.sc", 3), ("bsc", 3), ("b.com", 3), ("bcom", 3), ("bba", 3), ("b.a", 3), ("diploma", 2), ("intermediate", 1), ("hsc", 1), ("12th", 1), ("ssc", 0), ("10th", 0)]


def _degree_level(s):
    s = (s or "").lower()
    if re.match(r"^\s*be\b", s):
        return 3
    if re.match(r"^\s*me\b", s):
        return 4
    return max([v for k, v in _DEGREE_LEVEL if k in s] or [0])


def _education(lines, labels):
    idx = [i for i, l in enumerate(labels) if l == "education"]
    if not idx:
        idx = [i for i, ln in enumerate(lines) if _DEGREE_RE.search(ln) and len(ln) < 160 and labels[i] not in ("summary", "experience", "projects")]
    pool = set(idx)
    out = []
    for i in idx:
        ln = lines[i].strip(" •")
        if not ln or len(ln) > 220:
            continue
        m = _DEGREE_RE.search(ln)
        if not m or re.match(r"(?i)^\s*(?:course|examination|qualification|degree)\s*/", ln):
            continue
        if re.search(r"(?i)\b(?:year of passing|institution/university)\b", ln):
            continue
        tail = re.sub(r"(?i)^\s*(?:education|educational\s+qualifications?|qualifications?)\s*[:\-–]\s*", "", ln[m.start():])
        deg_part = re.split(r"\s*[|–—]\s*|\s+-\s+|,\s*(?=[^,]*\b(?:university|college|institute|school|academy|iit|nit|vtu|jntu|board)\b)|,\s*(?=(?:19|20)\d{2})|\s+from\s+|\s*-\s*(?=\d{4})", tail, maxsplit=1, flags=re.I)[0]
        deg = re.sub(r"\s+", " ", deg_part).strip(" ,.-–|")
        deg = re.sub(r"(?i)\s*[-–,]?\s*(?:19|20)\d{2}\b.*$", "", deg).strip(" ,.-–")
        window = [ln] + [lines[j].strip(" •") for j in (i + 1, i + 2, i - 1, i - 2) if 0 <= j < len(lines) and j in pool]
        inst = ""
        segs = re.split(r"\s*\|\s*|\s+[–—-]\s+|,\s*|\s+from\s+", ln[m.end():])
        inst = next((s.strip(" .") for s in segs if _INST_RE.search(s)), "")
        if not inst:
            for j in (i + 1, i - 1, i + 2, i - 2):
                if 0 <= j < len(lines) and j in pool:
                    cand = lines[j].strip(" •")
                    if cand and not _DEGREE_RE.search(cand) and _INST_RE.search(cand) and not re.search(r"(?i)year|grade|cgpa|percentage", cand):
                        inst = cand
                        break
        if not inst:
            j = i + 1
            if j < len(lines) and j in pool:
                cand = lines[j].strip(" •")
                if cand and not _DEGREE_RE.search(cand) and not re.fullmatch(r"[\d\s.%/:A-Za-z]{0,6}", cand) and len(cand.split()) <= 10 and not re.search(r"(?i)year|cgpa|gpa|%", cand):
                    inst = cand
        inst = re.sub(r"(?i)^(?:from|at)\s+", "", inst).strip(" .,")
        inst = re.sub(r"\s*\|\s*(?:graduated|year).*$", "", inst, flags=re.I).strip()
        win = " ".join([ln] + [lines[j].strip() for j in (i + 1,) if j < len(lines) and j in pool and not _DEGREE_RE.search(lines[j])])
        yrs = sorted({int(y) for y in re.findall(r"\b(19[7-9]\d|20[0-4]\d)\b", " ".join([ln] + [lines[j] for j in (i + 1, i + 2) if 0 <= j < len(lines) and j in pool and not _DEGREE_RE.search(lines[j])]))})
        g = re.search(r"(?i)\d(?:\.\d+)?\s*/\s*10\b|(?:cgpa|gpa)\s*[:\-]?\s*\d(?:\.\d+)?|\d(?:\.\d+)?\s*(?:cgpa|gpa)|\d{2}(?:\.\d+)?\s*%", win)
        spec = ""
        sm = re.search(r"(?i)\(([^)]{2,50})\)|[-–,]\s*((?:computer|electronics|electrical|mechanical|civil|information|chemical|physics|chemistry|math|commerce|finance|marketing|eee|ece|cse|it|ec|cs)[A-Za-z &]{0,40})", ln[m.start():])
        if sm:
            spec = (sm.group(1) or sm.group(2) or "").strip()
        out.append({"degree": deg[:90], "specialization": spec[:60], "institute": _smart_title(inst)[:110], "start_year": str(yrs[0]) if len(yrs) > 1 else "",
                    "end_year": str(yrs[-1]) if yrs else "", "grade": g.group(0).strip() if g else "", "location": _city_in(win)})
    uniq = []
    for e in out:
        if not any(_norm(e["degree"]) == _norm(u["degree"]) and _norm(e["institute"]) == _norm(u["institute"]) for u in uniq):
            uniq.append(e)
    return uniq[:6]


def _certifications(lines, labels, text):
    out = []
    for i, l in enumerate(labels):
        if l != "certs":
            continue
        s = lines[i].strip(" •-*")
        s = re.sub(r"\s*\[[^\]]*\]\s*$", "", s).strip()
        if not (4 < len(s) < 140) or re.match(r"(?i)^\(?\s*(?:id|credential)\s*[:#]", s) or re.search(r"(?i)notice|ctc|salary|expected", s):
            continue
        if re.fullmatch(r"[\d\s()/.\-:]+", s):
            continue
        if out and (s[:1].islower() or re.match(r"^(?:Cloud Developer|Developer|Associate|Specialist|Professional|Administrator|Consultant)\b", s) and not re.search(r"(?i)certified|certification|certificate", s)):
            out[-1] = out[-1] + " " + s
            continue
        out.append(s)
    for m in re.finditer(r"(?i)\b(?:(?:AWS|Azure|Google Cloud|GCP|Oracle|SAP|Salesforce|Microsoft|Cisco|Red Hat|Kubernetes|HashiCorp|Databricks|Snowflake)\s+Certified[^\n.,;|]{0,60}|"
                         r"Certified\s+(?:Kubernetes|Scrum|Salesforce|Platform|OmniStudio|Administrator|Developer|Associate)[^\n.,;|]{0,50}|\b(?:PMP|CSM|CISSP|CEH|CCNA|CCNP|PRINCE2|ITIL\s*(?:v4|Foundation)?|"
                         r"AZ-\d{3}|MB-\d{3}|PL-\d{3}|DP-\d{3}|AI-\d{3}|SC-\d{3}|PD1|PD2)\b[^\n.,;|]{0,60})", text):
        c = m.group(0).strip()
        if not any(_norm(c)[:25] in _norm(o) or _norm(o)[:25] in _norm(c) for o in out):
            out.append(c)
    return out[:20]


def _projects(lines, labels, extra):
    idx = [i for i, l in enumerate(labels) if l == "projects"]
    blocks, cur = [], []
    for i in idx:
        s = lines[i].strip()
        if not s:
            continue
        if re.match(r"(?i)^\s*(?:project\s*(?:#?\s*\d+|name|title)?\s*[:#\-–]|•\s*[A-Z][^.]{2,60}$)", s) or (_header_like(s) and len(s) < 80 and not s.startswith("•") and cur and len(cur) > 2):
            if cur:
                blocks.append(cur)
            cur = [s]
        else:
            cur.append(s)
    if cur:
        blocks.append(cur)
    out = []
    for b in blocks[:10]:
        title = re.sub(r"(?i)^\s*(?:•\s*)?project\s*(?:#?\s*\d+|name|title)?\s*[:#\-–]\s*", "", b[0]).strip(" •:")
        if not title and len(b) > 1:
            title = b[1]
            b = b[1:]
        body = " ".join(x.strip(" •") for x in b[1:])
        role = re.search(r"(?i)\brole\s*[:\-]\s*([^\n•]{3,60}?)(?=\s+(?:duration|client|organi|environment|project|$))", body + " ")
        client = re.search(r"(?i)\bclient\s*[:\-]\s*([^\n•]{2,60}?)(?=\s+(?:role|duration|organi|environment|brand|project|$)|\.)", body + " ")
        org = re.search(r"(?i)\borgani[sz]ation\s*[:\-]\s*([^\n•]{2,40}?)(?=\s+(?:client|role|duration|$))", body + " ")
        rng = _RANGE_RE.search(body)
        ts = re.search(r"(?i)(?:technolog(?:y|ies)|tech\s*stack|environment|tools)\s*[:\-]\s*([^\n•]{3,160})", body)
        out.append({"project_name": title[:120], "role": role.group(1).strip() if role else "", "organization": (org.group(1).strip() if org else (client.group(1).strip() if client else "")),
                    "start_date": rng.group(1) if rng else "", "end_date": rng.group(2) if rng else "", "description": body[:600],
                    "tech_stack": ts.group(1).strip() if ts else ", ".join(extract_skills(" ".join(b))[:8])})
    for e in extra:
        if len(out) >= 12:
            break
        out.append({"project_name": e.get("client") or e.get("company") or "Project", "role": _smart_title(e.get("role", "")), "organization": e.get("company", ""),
                    "start_date": _fmt_month(e["start"]), "end_date": "Present" if e["now"] else _fmt_month(e["end"]), "description": "", "tech_stack": ""})
    return out


# =====================================================================================
# 11. RESUME PARSER
# =====================================================================================
_TOTAL_EXP_RE = re.compile(r"(?i)(?:(?:total|overall|having|with|over|around|about|nearly|almost|approx\.?|approximately|more\s+than|of)\s+){0,3}(\d{1,2}(?:\.\d{1,2})?)\s*\+?\s*(?:years?|yrs?)"
                           r"(?:\s*(?:and|&|,)?\s*(\d{1,2})\s*(?:months?|mos?))?\s*(?:of\s+)?(?:(?:total|overall|it|professional|industry|work|working|hands[\s\-]*on|rich|relevant|extensive|"
                           r"progressive|cumulative|software|technical|corporate)\s+){0,3}(?:experience|exp\b)(?!\s+(?:in|with|on)\s+(?!the\s+(?:it|software)))")
_EXP_LABEL_RE = re.compile(r"(?i)(?:total\s+)?(?:work\s+)?experience\s*[:\-–]\s*(\d{1,2}(?:\.\d{1,2})?)\s*\+?\s*(?:years?|yrs?)(?:\s*(\d{1,2})\s*(?:months?|mos?))?")


def _claimed_years(text):
    """Largest explicit total-experience statement in the top part of the resume."""
    head = text[:max(2500, len(text) // 3)]
    vals = []
    for rx in (_EXP_LABEL_RE, _TOTAL_EXP_RE):
        for m in rx.finditer(head):
            y = float(m.group(1)) + (int(m.group(2)) / 12.0 if m.group(2) else 0)
            if 0 < y <= 45:
                vals.append(y)
    return max(vals) if vals else 0.0


def _headline(lines, labels, name_idx, name_toks):
    """Role line printed near the name ('Senior Frontend Developer', 'SFCC TECH LEAD')."""
    cands = []
    for i in list(name_idx):
        for j in range(i, min(len(lines), i + 4)):
            s = lines[j].strip()
            if j == i and name_toks:
                rest = s
                for t in name_toks:
                    rest = re.sub(r"(?i)^\s*" + re.escape(t) + r"\b", "", rest).strip()
                s = rest
            if not s or "@" in s or re.search(r"\d{6,}", s) or labels[j].startswith("heading"):
                continue
            s = re.split(r"\s+\|\s+", s)[0].strip()
            if _is_roleish(s) and len(s) <= 70 and not s.endswith(".") and not re.match(r"(?i)^(?:to|a|an|i|my|as)\b", s):
                cands.append(s)
                break
    for i, ln in enumerate(lines[:12]):
        s = ln.strip()
        if s and _is_roleish(s) and len(s.split()) <= 7 and "@" not in s and not s.endswith(".") and labels[i] in ("header", "contact") and not re.match(r"(?i)^(?:to|a|an|i|my|as)\b", s):
            cands.append(re.split(r"\s+\|\s+", s)[0])
    return _smart_title(cands[0]) if cands else ""


def _summary_role(text):
    m = re.search(r"(?:^|[.\n]\s*)(?:(?:a|an|as|motivated|experienced|seasoned|certified|passionate|dedicated|results?[\s\-]driven|highly|skilled|accomplished|dynamic|proactive|senior|innovative)\s+)*"
                  r"((?:[A-Z][\w/+#.&\-]*\s+){0,4}(?:Engineer|Developer|Consultant|Architect|Analyst|Administrator|Tester|Designer|Specialist|Manager|Lead))\b", text)
    if not m:
        return ""
    role = re.sub(r"(?i)^(?:(?:motivated|experienced|seasoned|certified|passionate|dedicated|highly|skilled|accomplished|dynamic|proactive|innovative|results?[\s\-]driven|an?|as)\s+)+", "", m.group(1).strip())
    return role


def parse_resume(text, today=None, filename=None):
    """Resume text -> structured profile. `filename` (optional) improves name / experience detection
    for portal exports such as 'Naukri_FirstLast5y_3m.pdf'. Empty or scanned input -> {'error': ..., 'parsed': False}."""
    today = today or date.today()
    t = _clean(text)
    if len(t) < 60 or len(re.findall(r"[A-Za-z]{3,}", t)) < 20:
        return {"error": "insufficient_text: the file looks empty or scanned (image only). Please upload a text-based PDF or DOCX.", "parsed": False}
    lines = t.split("\n")
    labels, spans = _sections(lines)
    notes = []
    emails = _emails(t)
    phones = _phones(t)
    li_m = re.search(r"(?i)(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|pub)/([A-Za-z0-9\-_%.]+)", t.replace(" -\n", "-").replace("-\n", "-"))
    linkedin = ("https://www.linkedin.com/in/" + li_m.group(1).rstrip("./-")) if li_m else ""
    gh = re.search(r"(?i)(?:https?://)?(?:www\.)?(?:github\.com|gitlab\.com|behance\.net|dribbble\.com)/[\w\-./]+", t)
    _pick_name.last_score = 0
    name_toks, name_notes = _pick_name(lines, labels, t, filename, emails, li_m.group(1) if li_m else "")
    nscore = getattr(_pick_name, "last_score", 0)
    name_conf = "high" if nscore >= 40 else "medium" if nscore >= 25 else "low"
    if name_notes and any("file name" in n or "e-mail" in n for n in name_notes):
        name_conf = "low"
    notes += name_notes
    name_idx = []
    if name_toks:
        for i, ln in enumerate(lines[:80]):
            if name_toks[0].lower() in ln.lower() and (len(name_toks) == 1 or name_toks[-1].lower() in " ".join(lines[i:i + 4]).lower()):
                name_idx.append(i)
                if len(name_toks) > 1 and len(ln.split()) == 1:
                    name_idx += [i + 1, i + 2]
                break
    first = name_toks[0] if name_toks else ""
    last = name_toks[-1] if len(name_toks) > 1 else ""
    middle = " ".join(name_toks[1:-1]) if len(name_toks) > 2 else ""
    if first and len(first.rstrip(".")) == 1 and len(name_toks) > 1:     # 'K Ramesh' -> Ramesh K; 'M. Pavan Kumar' -> Pavan Kumar M
        lead = []
        rest = list(name_toks)
        while rest and len(rest[0].rstrip(".")) == 1:
            lead.append(rest.pop(0))
        if rest:
            name_toks = rest + lead
            first = name_toks[0]
            last = name_toks[-1] if len(name_toks) > 1 else ""
            middle = " ".join(name_toks[1:-1]) if len(name_toks) > 2 else ""

    work, extra_projects = _work_entries(lines, labels, today, set(name_idx))
    computed = _union_months([w["_iv"] for w in work]) / 12.0 if work else 0.0
    claimed = _claimed_years(t)
    _, fn_exp, _ = _filename_name(filename)
    if fn_exp is not None:
        yoe = fn_exp / 12.0
        notes.append("experience taken from the portal file name")
    else:
        yoe = max(claimed, computed)
        if claimed and computed and abs(claimed - computed) > 2:
            notes.append("stated experience (%.1f yrs) differs from job dates (%.1f yrs)" % (claimed, computed))
    yoe = float(int(yoe * 10 + 0.5)) / 10.0

    skill_spans = [(a, b) for n, a, b in spans if n == "skills"]
    ctx = _skill_context_lines("\n".join(lines), skill_spans)
    ranked, counts, firstpos, where = extract_skills(t, with_counts=True, skill_line_idx=ctx, _detail=True)
    skill_lines = set()
    for a, b in skill_spans:
        skill_lines.update(range(a, b))
    exp_lines = {i for i, l in enumerate(labels) if l in ("experience", "projects")}
    score = {}
    for s in ranked:
        w = where.get(s, set())
        score[s] = counts[s] + (3 if w & skill_lines else 0) + (2 if w & exp_lines else 0)
    skills = sorted(ranked, key=lambda s: (-score[s], firstpos[s]))[:120]

    cur = next((w for w in work if w["_now"]), work[0] if work else None)
    head = _headline(lines, labels, name_idx[:1], name_toks)
    designation = head or (cur["role"] if cur and cur["role"] else "") or _smart_title(_summary_role(t))
    company = cur["company"] if cur else ""

    # location: contact/header block -> labelled address/location -> personal section -> current job -> phone country
    loc = ""
    hdr = "\n".join(lines[i] for i in range(min(len(lines), 40)) if labels[i] in ("header", "contact") or i in name_idx)
    m = re.search(r"(?im)^\s*(?:current\s*|present\s*)?(?:location|city|address|residence|based\s*(?:in|at))\s*[:\-–]?\s*(.{3,120})$", t)
    for src in (hdr, m.group(1) if m else "", "\n".join(lines[i] for i, l in enumerate(labels) if l in ("personal", "contact"))):
        c = _city_in(src)
        if c:
            loc = c
            break
    if not loc:
        sm = _STATE_RE.search(hdr)
        if sm:
            cm = _COUNTRY_RE.search(hdr[sm.end():sm.end() + 30])
            loc = sm.group(1) + (", " + cm.group(1) if cm else "")
    if not loc and cur and cur.get("location"):
        loc = cur["location"]
    if not loc:
        c = _city_in(t[:1500])
        loc = c
    if not loc and phones and phones[0][1] and phones[0][1] != "91":
        loc = _CC.get(phones[0][1], "")
        if loc:
            notes.append("location inferred from phone country code")
    pin = ""
    pm = re.search(r"(?i)(?:pin\s*(?:code)?|zip|postal\s*code)?\s*[:\-–]?\s*\b([1-9]\d{2}\s?\d{3})\b", "\n".join(lines[i] for i, l in enumerate(labels) if l in ("personal", "contact", "header")))
    if pm and not re.search(r"\d{7,}", pm.group(0)) and re.search(r"(?i)pin|address|" + (re.escape(loc) if loc else "zzz"), "\n".join(lines[i] for i, l in enumerate(labels) if l in ("personal", "contact", "header"))):
        pin = pm.group(1).replace(" ", "")

    np_m = re.search(r"(?i)notice\s*period\s*[:\-–]?\s*(\d+)\s*(day|week|month)|(\d+)\s*(day|week|month)s?\s*notice", t)
    if re.search(r"(?i)\bimmediate(?:ly)?\s*(?:joiner|available|joining)|available\s+immediately|immediately\s+available|notice\s*period\s*[:\-–]?\s*immediate", t):
        notice = 0
        notes.append("immediate joiner")
    elif np_m:
        num = int(np_m.group(1) or np_m.group(3))
        unit = (np_m.group(2) or np_m.group(4)).lower()
        notice = num * {"day": 1, "week": 7, "month": 30}[unit]
    else:
        notice = 0

    def ctc(label):
        mm = re.search(r"(?i)(?:" + label + r")\s*(?:ctc|salary|compensation|package)?\s*[:\-–]?\s*((?:rs\.?|inr|usd|aed|\$|₹)?\s*[\d.,]+\s*(?:lpa|lakhs?|lacs?|l\b|k\b|cr\b|per\s+annum|pa\b|p\.a\.?|per\s+month|pm\b)?)", t)
        return mm.group(1).strip() if mm and re.search(r"\d", mm.group(1)) else ""

    rel = []
    for s in skills[:30]:
        ex = re.search(r"(?i)(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience\s+)?(?:in|with|on)\s+(?:the\s+)?" + re.escape(s) + r"\b", t)
        if ex:
            y = float(ex.group(1))
        else:
            months = _union_months([w["_iv"] for w in work if re.search(r"(?i)(?<![\w])" + re.escape(s) + r"(?![\w])", w["role"] + " " + w["description"] + " " + w["company"])])
            y = round(months / 12.0, 1)
        if y > 0:
            rel.append({"skill": s, "years": min(y, yoe) if yoe else y})

    edu = _education(lines, labels)
    certs = _certifications(lines, labels, t)
    projects = _projects(lines, labels, extra_projects)
    summary = " ".join(lines[i].strip() for i, l in enumerate(labels) if l == "summary" and lines[i].strip())
    summary = re.sub(r"\s+", " ", summary)[:1000]
    status = ""
    if cur and cur["_now"]:
        status = "Freelancer" if re.search(r"(?i)freelanc", (cur["role"] or "") + " " + t[:600]) else "Employed"
    elif work:
        status = "Not currently employed" if (today.year * 12 + today.month - 1) - work[0]["_iv"][1] > 2 else "Employed"
    elif edu and yoe < 1:
        status = "Fresher"
    for w in work:
        w.pop("_iv", None)
        w.pop("_now", None)
    if not emails:
        notes.append("email not found")
    if not phones:
        notes.append("phone not found")
    if not work:
        notes.append("no dated work history found")
    return {
        "first_name": first, "middle_name": middle, "last_name": last, "full_name": " ".join(x for x in (first, middle, last) if x), "name_confidence": name_conf,
        "email": emails[0] if emails else "", "alternate_email": emails[1] if len(emails) > 1 else "",
        "phone": phones[0][0] if phones else "", "alternate_phone": phones[1][0] if len(phones) > 1 else "",
        "address": (re.search(r"(?im)^\s*address\s*[:\-]\s*([^\n]{5,150})", t) or [None, ""])[1].strip(), "location": loc, "pincode": pin,
        "linkedin": linkedin, "other_social": gh.group(0) if gh else "",
        "current_role": designation, "designation": designation, "current_company": company,
        "current_ctc": ctc("current|present"), "expected_ctc": ctc("expected|expecting"),
        "years_of_experience": yoe, "years_from_job_dates": round(computed, 1), "years_stated": round(claimed, 1), "notice_period_days": notice,
        "employment_status": status, "core_skills": skills, "relevant_experience": rel, "education": edu, "certifications": certs,
        "work_experience": work[:15], "projects": projects, "summary": summary,
        "parser": "nlp_engine", "engine_version": ENGINE_VERSION, "parsed": True, "extraction_notes": notes,
    }


# =====================================================================================
# 12. JD PARSER + MATCHING
# =====================================================================================
_MUST_HEAD = re.compile(r"(?i)\b(must[\s\-]*have|mandatory|required|requirements|primary\s+skills?|key\s+skills|essential|minimum\s+qualifications?|core\s+skills|technical\s+skills|what\s+you(?:'ll)?\s+need|you\s+have|skills\s+required)\b")
_NICE_HEAD = re.compile(r"(?i)\b(nice[\s\-]*to[\s\-]*have|good[\s\-]*to[\s\-]*have|preferred|desirable|desired|plus|bonus|optional|added\s+advantage|secondary\s+skills?|an\s+advantage|would\s+be\s+a\s+plus)\b")


def parse_jd(text):
    """Structured requirements from a job description."""
    t = _clean(text)
    lines = t.split("\n")
    title = ""
    m = re.search(r"(?im)^\s*(?:job\s*title|position|role|designation|title)\s*[:\-–]\s*(.{3,90})$", t)
    if m:
        title = m.group(1).strip()
    else:
        for ln in lines[:8]:
            s = ln.strip(" •*#")
            if s and _is_roleish(s) and len(s) < 90 and not s.endswith("."):
                title = s
                break
    if not title:
        title = _summary_role(re.sub(r"(?i)\b(?:hiring|looking\s+for|seeking|need|require)\s+(?:an?\s+)?", ". ", t[:400]))
    yrs_min = yrs_max = 0.0
    m = re.search(r"(?i)(\d{1,2}(?:\.\d)?)\s*(?:\+\s*)?(?:-|–|to)\s*(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)", t)
    if m:
        yrs_min, yrs_max = float(m.group(1)), float(m.group(2))
    else:
        m = (re.search(r"(?i)(?:experience|exp)\s*(?:required)?\s*[:\-–]\s*(?:minimum|min\.?|at\s+least)?\s*(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)", t)
             or re.search(r"(?i)(?:minimum|min\.?|at\s+least|over|more\s+than)?\s*(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+\w+){0,4}?\s+(?:experience|exp)", t))
        if m:
            yrs_min = float(m.group(1))
    must, nice, all_sk = [], [], []
    mode = None
    ctx = _skill_context_lines(t)
    clauses = []
    for i, ln in enumerate(lines):
        parts = [x for x in re.split(r"(?<=[A-Za-z0-9)])[.;](?=\s+[A-Z])|;\s*", ln) if x.strip()] if len(ln) > 90 else [ln]
        clauses += [(i, x) for x in parts]
    for i, ln in clauses:
        s = ln.strip()
        if not s:
            continue
        head = len(s) < 70 and (s.endswith(":") or s.isupper() or _heading_of(s))
        if head and _NICE_HEAD.search(s):
            mode = "nice"
        elif head and _MUST_HEAD.search(s):
            mode = "must"
        elif head and re.search(r"(?i)responsibilit|about|company|benefit|what\s+we\s+offer|role\s+overview|job\s+description", s):
            mode = None
        sk = extract_skills(s, skill_line_idx={0} if i in ctx else set())
        items = {_k(x) for x in re.split(r"[,;|•/:()]|\band\b", s) if x.strip()}
        sk = [x for x in sk if not (_FAMILY.get(x) in ("PM_METHOD", "BUSINESS", "SECURITY", "INFRA") and any(_ALIAS.get(kk) == x and kk in _AMBIG for kk in _ALIAS) and not any(_ALIAS.get(it) == x for it in items))]
        line_nice = bool(_NICE_HEAD.search(s)) and not head
        line_must = bool(re.search(r"(?i)\b(must|mandatory|required|requires?|strong|expert|expertise\s+in|hands[\s\-]*on|proficien\w*|deep|solid|extensive|"
                                   r"experience\s+(?:in|with|on|of)|skilled\s+in|working\s+knowledge|good\s+knowledge|in[\s\-]depth)\b", s)) and not line_nice
        for x in sk:
            if x not in all_sk:
                all_sk.append(x)
            if mode == "nice" or line_nice:
                if x not in must and x not in nice:
                    nice.append(x)
            elif mode == "must" or line_must:
                if x not in must:
                    must.append(x)
                if x in nice:
                    nice.remove(x)
    title_sk = extract_skills(title) if title else []
    for x in title_sk:
        if x not in must:
            must.insert(0, x)
        if x in nice:
            nice.remove(x)
        if x not in all_sk:
            all_sk.insert(0, x)
    other = [x for x in all_sk if x not in must and x not in nice]
    edu_level = _degree_level(" ".join(re.findall(r"(?i)(?:b\.?\s?tech|b\.?e\b|bachelor[^\n,;]{0,30}|master[^\n,;]{0,30}|m\.?\s?tech|mca|mba|phd|ph\.d|degree|graduate)", t)))
    certs = sorted(set(m.group(0) for m in re.finditer(r"(?i)\b(?:pmp|csm|cissp|ceh|ccna|ccnp|itil|prince2|(?:aws|azure|sap|salesforce|google|oracle)\s+certifi\w+(?:\s+[\w\-]+){0,4}|platform\s+developer\s+(?:i{1,2}|1|2)|az-\d{3}|mb-\d{3})\b", t)))
    loc = _city_in(t[:1500])
    mode_w = "Remote" if re.search(r"(?i)\bremote\b|work\s+from\s+home|wfh", t) else "Hybrid" if re.search(r"(?i)\bhybrid\b", t) else "Onsite" if re.search(r"(?i)\bon[\s\-]?site|work\s+from\s+office|wfo", t) else ""
    return {"title": title, "min_years": yrs_min, "max_years": yrs_max, "must_have": must, "nice_to_have": nice, "other_skills": other, "all_skills": all_sk,
            "education_level": edu_level, "certifications": certs, "location": loc, "work_mode": mode_w, "title_skills": title_sk}


def _family_profile(skills_with_weight):
    prof = {}
    for s, w in skills_with_weight:
        f = _FAMILY.get(s)
        if f and f not in _GENERIC_FAMILIES:
            prof[f] = prof.get(f, 0.0) + w
    return prof


def _cos(a, b):
    num = sum(a[k] * b.get(k, 0.0) for k in a)
    da = sum(v * v for v in a.values()) ** 0.5
    db = sum(v * v for v in b.values()) ** 0.5
    return num / (da * db) if da and db else 0.0


_TITLE_SYN = {"dev": "developer", "devs": "developer", "engg": "engineer", "sr": "senior", "jr": "junior", "mgr": "manager", "programmer": "developer", "swe": "engineer",
              "sde": "engineer", "frontend": "front end", "front-end": "front end", "backend": "back end", "back-end": "back end", "fullstack": "full stack"}
_TITLE_STOP = {"senior", "junior", "lead", "sr", "jr", "i", "ii", "iii", "principal", "staff", "associate", "the", "and", "of", "for", "in", "with", "on", "a", "an", "-", "/", "&"}


def _title_tokens(s):
    toks = re.findall(r"[a-z0-9+#/.]+", (s or "").lower())
    out = set()
    for t in toks:
        t = _TITLE_SYN.get(t, t)
        for x in t.split():
            if x not in _TITLE_STOP and len(x) > 1:
                out.add(x)
    return out


def analyze_match(resume_text, jd_text, today=None, resume_filename=None, jd_meta=None):
    """Explainable resume-vs-JD match. Keys are compatible with what /api/analyze-match returned before."""
    today = today or date.today()
    r_text, j_text = _clean(resume_text), _clean(jd_text)
    if len(r_text) < 60:
        return {"error": "The candidate has no readable resume text. Re-upload the resume.", "match_score": 0, "matching_skills": [], "missing_skills": []}
    if len(j_text) < 40:
        return {"error": "The job description is too short to analyse. Add the JD text to the job.", "match_score": 0, "matching_skills": [], "missing_skills": []}
    jd = parse_jd(j_text)
    if jd_meta:
        for k in ("min_years", "max_years"):
            if jd_meta.get(k):
                jd[k] = float(jd_meta[k])
        for s in jd_meta.get("required_skills", []) or []:
            for x in extract_skills(str(s), skill_line_idx={0}) or []:
                if x not in jd["must_have"]:
                    jd["must_have"].append(x)
                if x in jd["nice_to_have"]:
                    jd["nice_to_have"].remove(x)
                if x not in jd["all_skills"]:
                    jd["all_skills"].append(x)
    cand = parse_resume(r_text, today=today, filename=resume_filename)
    if cand.get("error"):
        return {"error": cand["error"], "match_score": 0, "matching_skills": [], "missing_skills": []}
    lines = r_text.split("\n")
    labels, spans = _sections(lines)
    ctx = _skill_context_lines(r_text, [(a, b) for n, a, b in spans if n == "skills"])
    _, counts, _, where = extract_skills(r_text, with_counts=True, skill_line_idx=ctx, _detail=True)
    have = set(counts)
    implied = {}
    for s in list(have):
        for p in _IMPLIES.get(s, []):
            implied.setdefault(p, s)
    exp_lines = {i for i, l in enumerate(labels) if l in ("experience", "projects")}
    recent_text = " ".join((w.get("role", "") + " " + w.get("description", "")) for w in cand["work_experience"][:2])
    recent = set(extract_skills(recent_text, skill_line_idx=set(range(len(recent_text.split("\n")))))) if recent_text.strip() else set()
    rel_years = {x["skill"]: x["years"] for x in cand.get("relevant_experience", [])}

    must = jd["must_have"] or []
    nice = jd["nice_to_have"] or []
    other = [s for s in jd["all_skills"] if s not in must and s not in nice]
    if not must and other:                    # JD without explicit sections: treat its skills as required
        must, other = other, []
    weights = {s: (1.5 if s in jd["title_skills"] else 1.0) for s in must}
    weights.update({s: 0.6 for s in other if s not in weights})
    weights.update({s: 0.35 for s in nice if s not in weights})

    evidence, matched, partial, missing = [], [], [], []
    got = 0.0
    for s, w in weights.items():
        if s in have:
            lines_of = where.get(s, set())
            in_work = bool(lines_of & exp_lines)
            strength = 1.0 if (s in recent or in_work or rel_years.get(s)) else 0.85
            how = ("used in recent role" if s in recent else "used in work history" if in_work else "listed in skills")
            if rel_years.get(s):
                how += " (~%g yrs)" % rel_years[s]
            evidence.append({"skill": s, "status": "matched", "weight": w, "evidence": how})
            matched.append(s)
            got += w * strength
        elif s in implied:
            evidence.append({"skill": s, "status": "matched", "weight": w, "evidence": "implied by %s" % implied[s]})
            matched.append(s)
            got += w * 0.9
        else:
            rel = sorted(x for x in _REL.get(s, set()) if x in have)
            if rel:
                evidence.append({"skill": s, "status": "related", "weight": w, "evidence": "has related: %s" % ", ".join(rel[:3])})
                partial.append(s)
                got += w * 0.45
            else:
                evidence.append({"skill": s, "status": "missing", "weight": w, "evidence": "not found in resume"})
                missing.append(s)
    total_w = sum(weights.values())
    skill_score = (got / total_w * 100) if total_w else None
    must_hit = [s for s in must if s in matched]
    must_rel = [s for s in must if s in partial]
    must_cov = ((len(must_hit) + 0.45 * len(must_rel)) / len(must)) if must else None

    # experience
    yrs = cand["years_of_experience"]
    need, cap_yrs = jd["min_years"], jd["max_years"]
    if need:
        if yrs >= need:
            exp_score = 100 if not cap_yrs or yrs <= cap_yrs + 3 else 85
        else:
            exp_score = max(0, round(yrs / need * 100) - (10 if yrs < need - 2 else 0))
    else:
        exp_score = 80 if yrs else 50

    # role / domain alignment
    jd_prof = _family_profile([(s, weights.get(s, 0.5)) for s in jd["all_skills"]])
    cv_prof = _family_profile([(s, min(counts[s], 6)) for s in counts])
    domain = _cos(jd_prof, cv_prof) if jd_prof else None
    jd_dom = max(jd_prof, key=jd_prof.get) if jd_prof else ""
    cv_dom = max(cv_prof, key=cv_prof.get) if cv_prof else ""
    tt_jd = _title_tokens(jd["title"])
    tt_cv = _title_tokens(cand["designation"] + " " + " ".join(w.get("role", "") for w in cand["work_experience"][:3]))
    title_sim = (len(tt_jd & tt_cv) / len(tt_jd)) if tt_jd else None
    parts = [x for x in (domain, title_sim) if x is not None]
    role_score = round((0.65 * (domain or 0) + 0.35 * (title_sim or 0)) * 100) if domain is not None and title_sim is not None else round((parts[0] if parts else 0.5) * 100)

    # text similarity (secondary signal)
    tfidf = 0.0
    if TfidfVectorizer is not None:
        try:
            stop = list(ENGLISH_STOP_WORDS | {"experience", "years", "year", "work", "working", "team", "teams", "skills", "skill", "knowledge", "ability", "strong", "good", "excellent",
                                              "responsibilities", "requirements", "candidate", "role", "job", "company", "including", "using", "worked", "project", "projects"})
            vec = TfidfVectorizer(stop_words=stop, ngram_range=(1, 2), sublinear_tf=True, token_pattern=r"(?u)\b[a-z][a-z0-9_+#./]*[a-z0-9+#]\b")
            mtx = vec.fit_transform([j_text.lower() + " " + " ".join("sk_" + _k(s) for s in jd["all_skills"]), r_text.lower() + " " + " ".join("sk_" + _k(s) for s in have)])
            tfidf = min(100.0, float(cosine_similarity(mtx[0], mtx[1])[0, 0]) / 0.5 * 100)
        except ValueError:
            tfidf = 0.0

    # education & certifications
    cv_level = max([_degree_level(e["degree"]) for e in cand["education"]] or [0])
    jl = jd["education_level"]
    edu_score = 100 if (cv_level and cv_level >= jl) else 75 if (cv_level and jl - cv_level == 1) else 40 if jl and not cv_level else 70 if cv_level else 60
    cert_hits = [c for c in jd["certifications"] if _norm(c)[:12] in _norm(r_text)]
    cert_score = round(len(cert_hits) / len(jd["certifications"]) * 100) if jd["certifications"] else 100 if cand["certifications"] else 70

    # final score
    if skill_score is None:
        base = 0.45 * role_score + 0.35 * tfidf + 0.20 * exp_score
    else:
        base = 0.50 * skill_score + 0.18 * exp_score + 0.17 * role_score + 0.10 * tfidf + 0.05 * edu_score
    caps, reasons = [], []
    if must_cov is not None and must_cov < 0.5:
        caps.append(40 + must_cov * 30)
        reasons.append("fewer than half of the must-have skills are present")
    if need and yrs < need * 0.6:
        caps.append(55)
        reasons.append("experience is well below the minimum")
    if domain is not None and domain < 0.25 and jd_prof:
        caps.append(35)
        reasons.append("the candidate's background (%s) is a different domain from the JD (%s)" % (_FAMILY_LABEL.get(cv_dom, cv_dom or "unclear"), _FAMILY_LABEL.get(jd_dom, jd_dom)))
    score = int(round(min([base] + caps)))
    score = max(0, min(100, score))
    if score >= 80:
        rec = "Strong Match - Shortlist"
    elif score >= 65:
        rec = "Good Match - Interview"
    elif score >= 50:
        rec = "Partial Match - Review"
    elif score >= 35:
        rec = "Weak Match"
    else:
        rec = "Not a Fit"

    n_jd = len(weights)
    conf = "High" if n_jd >= 6 and len(r_text) > 1500 else "Medium" if n_jd >= 3 else "Low"
    conf_reason = ("%d JD skills compared" % n_jd) + ("" if conf != "Low" else "; the JD lists few concrete skills, so the score leans on role and text similarity")

    strengths, weaknesses = [], []
    if must:
        strengths.append("Must-have skills: %d of %d" % (len(must_hit), len(must))) if must_hit else None
    if matched:
        strengths.append("Matches: " + ", ".join(matched[:6]))
    if need and yrs >= need:
        strengths.append("%g yrs experience (JD asks %g%s)" % (yrs, need, "-%g" % cap_yrs if cap_yrs else "+"))
    if domain is not None and domain >= 0.6:
        strengths.append("Background fits the JD domain (%s)" % _FAMILY_LABEL.get(jd_dom, jd_dom))
    if cert_hits:
        strengths.append("Has required certification: " + ", ".join(cert_hits[:2]))
    miss_must = [s for s in must if s in missing]
    if miss_must:
        weaknesses.append("Missing must-have: " + ", ".join(miss_must[:6]))
    miss_other = [s for s in missing if s not in miss_must]
    if miss_other:
        weaknesses.append("Missing: " + ", ".join(miss_other[:6]))
    if partial:
        weaknesses.append("Only related experience for: " + ", ".join(partial[:5]))
    if need and yrs < need:
        weaknesses.append("%g yrs experience, below the %g yrs required" % (yrs, need))
    if need and cap_yrs and yrs > cap_yrs + 3:
        weaknesses.append("%g yrs may be over-qualified for a %g-%g yrs role" % (yrs, need, cap_yrs))
    if domain is not None and domain < 0.25 and jd_prof:
        weaknesses.append("Different domain: %s vs %s" % (_FAMILY_LABEL.get(cv_dom, cv_dom or "unclear"), _FAMILY_LABEL.get(jd_dom, jd_dom)))
    strengths = [s for s in strengths if s]

    who = cand.get("full_name") or "The candidate"
    role_now = cand["designation"] + (" at " + cand["current_company"] if cand["current_company"] else "") if cand["designation"] else ""
    summary = ["%s scores %d/100 (%s)." % (who, score, rec)]
    if must:
        s = "Covers %d of %d must-have skills" % (len(must_hit), len(must))
        if miss_must:
            s += " - missing %s" % ", ".join(miss_must[:5])
        if must_rel:
            s += "; related experience only for %s" % ", ".join(must_rel[:4])
        summary.append(s + ".")
    if need:
        summary.append("Experience: %g yrs against %g%s yrs required." % (yrs, need, "-%g" % cap_yrs if cap_yrs else "+"))
    elif yrs:
        summary.append("Experience: %g yrs." % yrs)
    if role_now:
        summary.append("Current role: %s%s." % (role_now, " - aligned with the JD" if (domain or 0) >= 0.6 else " - partly aligned" if (domain or 0) >= 0.3 else ""))
    if reasons:
        summary.append("Score capped because " + "; ".join(reasons) + ".")
    detail = " ".join(summary)

    questions = ["Walk me through a recent project where you used %s. What was your exact contribution?" % s for s in [x for x in must if x in matched][:2]]
    questions += ["The JD needs %s. What hands-on exposure do you have, and how quickly could you ramp up?" % s for s in miss_must[:3]]
    questions += ["You have %s experience - how would you apply it to %s?" % (next(iter(sorted(x for x in _REL.get(s, set()) if x in have)), "related"), s) for s in must_rel[:2]]
    if need:
        questions.append("Confirm your total and relevant experience (JD asks %g%s yrs)." % (need, "-%g" % cap_yrs if cap_yrs else "+"))
    questions.append("What is your current CTC, expected CTC and notice period?")
    learning = [{"skill": s, "resources": ["Hands-on project using %s" % s, "Official %s documentation / trail" % s, "Certification or course on %s" % s],
                 "estimated_hours": 40 if s in must else 20} for s in (miss_must + [x for x in missing if x not in miss_must])[:5]]
    return {
        "match_score": score, "recommendation": rec, "confidence": conf, "confidence_reason": conf_reason,
        "category_scores": {"skills_match": round(skill_score) if skill_score is not None else round(tfidf), "experience_match": exp_score, "education_match": edu_score,
                            "certifications_match": cert_score, "role_fit": role_score, "text_similarity": round(tfidf), "overall_fit": score},
        "matching_skills": matched, "missing_skills": miss_must + [x for x in missing if x not in miss_must], "partial_skills": partial,
        "strengths": strengths, "weaknesses": weaknesses, "detailed_analysis": detail, "executive_summary": detail,
        "skill_evidence": evidence,
        "jd_requirements": {"title": jd["title"], "min_years": need, "max_years": cap_yrs, "must_have": must, "nice_to_have": nice, "other_skills": other,
                            "education_level": jl, "certifications": jd["certifications"], "domain": _FAMILY_LABEL.get(jd_dom, jd_dom)},
        "candidate_snapshot": {"name": cand.get("full_name"), "designation": cand["designation"], "company": cand["current_company"], "years_of_experience": yrs,
                               "domain": _FAMILY_LABEL.get(cv_dom, cv_dom), "location": cand["location"]},
        "skill_gap": {"matching_skills": matched, "missing_skills": miss_must + [x for x in missing if x not in miss_must],
                      "gap_percentage": round(len(missing) / n_jd * 100) if n_jd else 0, "learning_path": learning, "total_jd_skills": n_jd, "total_resume_skills": len(have)},
        "interview_questions": {"technical": questions[:4], "skill_check": ["Rate yourself 1-10 on %s and give an example." % s for s in (must_hit[:3] + miss_must[:2])],
                                "behavioral": ["Describe a production issue you owned end-to-end.", "How do you handle changing requirements mid-sprint?",
                                               "Tell me about a time you disagreed with a stakeholder and how it was resolved."]},
        "pre_screening_questions": questions,
        "tfidf_similarity": round(tfidf, 1), "skill_coverage": None if skill_score is None else round(skill_score, 1),
        "resume_skills": sorted(have), "jd_skills": list(weights), "years_of_experience": yrs, "parser": "nlp_engine", "engine_version": ENGINE_VERSION,
    }
