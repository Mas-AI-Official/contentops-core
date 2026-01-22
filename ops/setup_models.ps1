# Content Factory - Model Setup Script
# Run as: .\setup_models.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Content Factory - Model Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$BASE_PATH = "D:\Ideas\content_factory"

# ============================================
# 1. Check Ollama is running
# ============================================
Write-Host "[1/3] Checking Ollama service..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host "Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "Ollama is not running. Starting Ollama..." -ForegroundColor Yellow
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -Method GET -TimeoutSec 5 -ErrorAction Stop
        Write-Host "Ollama started successfully" -ForegroundColor Green
    } catch {
        Write-Host "Failed to start Ollama. Please start it manually: ollama serve" -ForegroundColor Red
        exit 1
    }
}

# ============================================
# 2. Pull LLM Models
# ============================================
Write-Host ""
Write-Host "[2/3] Pulling LLM models..." -ForegroundColor Yellow

# Main model - high quality
Write-Host "Pulling llama3.1:8b (main model)..." -ForegroundColor Yellow
ollama pull llama3.1:8b
Write-Host "Main model ready" -ForegroundColor Green

# Fast model - for quick tasks like topic generation
Write-Host "Pulling llama3.2:3b (fast model)..." -ForegroundColor Yellow
ollama pull llama3.2:3b
Write-Host "Fast model ready" -ForegroundColor Green

# ============================================
# 3. Create Default Niche Templates
# ============================================
Write-Host ""
Write-Host "[3/3] Creating niche templates..." -ForegroundColor Yellow

$nichesPath = "$BASE_PATH\data\niches"

# Create niche directories and templates
$niches = @{
    "ai_tech" = @{
        description = "AI, tech news, and futuristic content"
        style = "narrator_broll"
        hashtags = @("ai", "tech", "future", "technology", "innovation", "chatgpt", "artificialintelligence")
        topics = @(
            "5 AI tools that will change how you work in 2024",
            "The truth about AI taking your job",
            "How to use ChatGPT like a pro",
            "AI features your phone has that you don't know about",
            "Why AI art is controversial",
            "The dark side of facial recognition",
            "How AI is revolutionizing healthcare",
            "Self-driving cars: Are we there yet?",
            "The AI tool that writes better than most humans",
            "Why tech companies are betting billions on AI"
        )
        prompt_hook = "Create a shocking or surprising hook about {topic} that makes viewers stop scrolling. Use a bold claim or counterintuitive statement. Keep it under 15 words."
        prompt_body = "Write an informative and engaging script about {topic}. Include 3-4 key points. Use simple language that anyone can understand. Make it conversational, not robotic. Target length: 45 seconds of speech."
        prompt_cta = "Write a call-to-action asking viewers to follow for more AI/tech content. Make it natural, not salesy. Under 10 words."
    }
    "finance_tax" = @{
        description = "Personal finance, tax tips, and money advice"
        style = "narrator_broll"
        hashtags = @("money", "finance", "taxes", "investing", "savings", "wealth", "financialfreedom", "moneytips")
        topics = @(
            "Tax deductions most people forget",
            "The 50/30/20 budget rule explained",
            "How to build an emergency fund fast",
            "Credit score myths that are costing you money",
            "Why rich people don't save money in banks",
            "The best time to file your taxes",
            "How to negotiate your salary",
            "Side hustles that actually pay well",
            "Investment mistakes beginners make",
            "How to retire early with FIRE"
        )
        prompt_hook = "Create an attention-grabbing hook about {topic} that appeals to people's desire to save or make money. Use urgency or reveal a secret. Under 15 words."
        prompt_body = "Write a clear, actionable script about {topic}. Include specific tips or steps people can take today. Avoid jargon - explain concepts simply. Target: 50 seconds of speech."
        prompt_cta = "Write a CTA encouraging viewers to follow for more money tips. Mention the value they'll get. Under 10 words."
    }
    "health" = @{
        description = "Health tips, wellness, and fitness motivation"
        style = "narrator_broll"
        hashtags = @("health", "wellness", "fitness", "healthy", "workout", "nutrition", "selfcare", "healthylifestyle")
        topics = @(
            "Morning habits that changed my life",
            "Foods you think are healthy but aren't",
            "The science of better sleep",
            "Why walking is the best exercise",
            "How to stay motivated to work out",
            "Water intake myths debunked",
            "Stretches you should do every day",
            "Mental health tips that actually work",
            "How to fix your posture",
            "The truth about protein supplements"
        )
        prompt_hook = "Create a hook about {topic} that makes health advice feel exciting and achievable. Challenge a common belief or promise a transformation. Under 15 words."
        prompt_body = "Write an encouraging, science-backed script about {topic}. Include practical tips anyone can start today. Be motivating without being preachy. Target: 50 seconds."
        prompt_cta = "Write a supportive CTA encouraging viewers to follow their health journey with you. Warm and encouraging. Under 10 words."
    }
    "travel" = @{
        description = "Travel tips, destinations, and adventure content"
        style = "slideshow"
        hashtags = @("travel", "wanderlust", "adventure", "explore", "vacation", "traveltips", "bucketlist", "travelgram")
        topics = @(
            "Hidden gems in Europe most tourists miss",
            "How to travel on a tight budget",
            "Airport hacks that save hours",
            "The best time to book flights",
            "Solo travel tips for beginners",
            "Countries where your dollar goes furthest",
            "Packing mistakes everyone makes",
            "How to get free hotel upgrades",
            "Safest countries for travelers",
            "Destinations that look like another planet"
        )
        prompt_hook = "Create a wanderlust-inducing hook about {topic} that makes viewers dream of traveling. Use vivid imagery or surprising facts. Under 15 words."
        prompt_body = "Write an exciting, practical script about {topic}. Include insider tips that feel like secrets. Make viewers feel like they're getting valuable travel intel. Target: 50 seconds."
        prompt_cta = "Write a CTA inviting viewers to follow for more travel inspiration and tips. Create FOMO. Under 10 words."
    }
    "comedy_stick_caption" = @{
        description = "Funny observations and relatable humor with stick figures"
        style = "stick_caption"
        hashtags = @("funny", "comedy", "relatable", "humor", "lol", "memes", "jokes", "viral")
        topics = @(
            "When you realize it's only Tuesday",
            "Introverts at parties be like",
            "The five stages of waking up early",
            "When your food arrives at a restaurant",
            "Adulting expectations vs reality",
            "That feeling when Friday finally hits",
            "Me pretending to understand directions",
            "When someone says 'we need to talk'",
            "Online shopping vs what arrives",
            "Monday morning vibes"
        )
        prompt_hook = "Write a relatable or funny opening line for a video about {topic}. Make it feel like an inside joke everyone gets. Conversational tone. Under 15 words."
        prompt_body = "Write a funny script about {topic} with comedic timing. Include 2-3 relatable scenarios or observations. Use pauses and punchlines effectively. Keep it clean and universally funny. Target: 30 seconds."
        prompt_cta = "Write a casual CTA that fits the comedy vibe. Something like asking to follow for more laughs. Under 10 words."
    }
}

foreach ($niche in $niches.Keys) {
    $nichePath = "$nichesPath\$niche"
    
    # Create directory
    if (-not (Test-Path $nichePath)) {
        New-Item -ItemType Directory -Path $nichePath -Force | Out-Null
    }
    
    # Write config.json
    $config = @{
        name = $niche
        description = $niches[$niche].description
        style = $niches[$niche].style
        hashtags = $niches[$niche].hashtags
        prompts = @{
            hook = $niches[$niche].prompt_hook
            body = $niches[$niche].prompt_body
            cta = $niches[$niche].prompt_cta
        }
    }
    $config | ConvertTo-Json -Depth 10 | Set-Content "$nichePath\config.json"
    
    # Write topics.json
    $topicsData = @{
        topics = $niches[$niche].topics
        used = @()
    }
    $topicsData | ConvertTo-Json | Set-Content "$nichePath\topics.json"
    
    Write-Host "Created template for: $niche" -ForegroundColor Green
}

# ============================================
# Summary
# ============================================
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Model Setup Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Models installed:" -ForegroundColor Yellow
Write-Host "  - llama3.1:8b (main model for scripts)" -ForegroundColor White
Write-Host "  - llama3.2:3b (fast model for topics)" -ForegroundColor White
Write-Host ""
Write-Host "Niche templates created:" -ForegroundColor Yellow
foreach ($niche in $niches.Keys) {
    Write-Host "  - $niche" -ForegroundColor White
}
Write-Host ""
Write-Host "You can now run: .\run_all.ps1" -ForegroundColor Cyan
