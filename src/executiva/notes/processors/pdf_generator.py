
import markdown
import re 
import html
import bleach


def create_acessability_pdf(title:str, ai_text:str) -> bytes:
    """Converte o resumo em Markdown num PDF com formatação de leitura acessível. Limpa o HTML gerado, escapa o título e devolve os bytes do PDF para o endpoint enviar ao cliente.
    """
    from weasyprint import HTML
    html_content = bleach.clean(
        markdown.markdown(_bionic_reader(ai_text)),
        tags={"p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "h1", "h2", "h3", "blockquote", "code", "pre"},
        attributes={},
        strip=True,
    )
    
    ll_html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4;
                margin: 2.5cm;
                @bottom-right {{
                    content: "Página " counter(page) " de " counter(pages);
                    font-family: 'Lexend', sans-serif;
                    font-size: 9pt;
                    color: #888;
                }}
            }}
            
            body {{
                font-family: 'Lexend', sans-serif; /* Fonte desenhada para melhorar a leitura (PHDA/Dislexia) */
                font-size: 14pt;
                line-height: 1.8;
                color: #2c3e50;
            }}
            
            /* GRADIENTES E BORDAS ARREDONDADAS */
            .header-inclusivo {{
                background: linear-gradient(135deg, #FCC067, #f6f490);
                padding: 30px;
                border-radius: 12px;
                margin-bottom: 40px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            
            h1 {{
                color: #ffffff;
                margin: 0;
                font-size: 26pt;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
            }}
            
            h2, h3 {{
                color: #e5a84b;
                margin-top: 30px;
            }}
            
            /* ÂNCORAS / HIGHLIGHTS */
            a.ancora-topo {{
                display: block;
                text-align: right;
                text-decoration: none;
                color: #FCC067;
                font-weight: bold;
                font-size: 11pt;
                margin-top: 30px;
            }}
        </style>
    </head>
    <body>
        <!-- ÂNCORA: ID para onde a página pode saltar -->
        <div id="inicio" class="header-inclusivo">
            <h1>Resumo Inclusivo</h1>
            <p style="color: #555; font-size: 12pt; margin-top: 10px;"><b>Tópico:</b> {html.escape(title or "")}</p>
        </div>
        
        <div class="conteudo">
            {html_content}
        </div>
        
        <!-- LINK QUE VAI PARA A ÂNCORA -->
        <a href="#inicio" class="ancora-topo">↑ Voltar ao Início</a>
    </body>
    </html>
    """
    return HTML(string=ll_html).write_pdf()

    
    
    
def _bionic_reader(text:str) -> str:
    
    """Aplica leitura biónica ao texto, colocando a primeira parte de cada palavra a negrito para facilitar a orientação visual durante a leitura.
    """
    def bionic_wording(match):
        """Formata uma palavra encontrada pela expressão regular: palavras curtas ficam totalmente a negrito e as restantes ficam com a primeira metade destacada.
        """
        word = match.group(0)
        if len(word) <=3:
            return f"<b>{word}</b>"
        
        half_length = (len(word)+1) // 2
        return f"<b>{word[:half_length]}</b>{word[half_length:]}"
    return re.sub(r'\b\w+\b', bionic_wording, text)
