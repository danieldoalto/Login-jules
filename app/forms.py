from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from .models import User # Para verificar se o e-mail já existe

# Para a pergunta matemática simples
import random

class RegistrationForm(FlaskForm):
    email = StringField('E-mail',
                        validators=[DataRequired(message="Este campo é obrigatório."),
                                    Email(message="E-mail inválido.")])
    password = PasswordField('Senha',
                             validators=[DataRequired(message="Este campo é obrigatório."),
                                         Length(min=8, message="A senha deve ter pelo menos 8 caracteres.")])
    confirm_password = PasswordField('Confirme a Senha',
                                     validators=[DataRequired(message="Este campo é obrigatório."),
                                                 EqualTo('password', message="As senhas não coincidem.")])

    # Verificação humana simples
    num1 = IntegerField('Num1', render_kw={'style': 'display:none;'}) # Escondido, valor definido na rota
    num2 = IntegerField('Num2', render_kw={'style': 'display:none;'}) # Escondido, valor definido na rota
    math_answer = IntegerField('Quanto é <span id="num1_display"></span> + <span id="num2_display"></span>?',
                               validators=[DataRequired(message="Responda à pergunta de verificação.")])

    submit = SubmitField('Registrar')

    def validate_email(self, email):
        """Verifica se o e-mail já está cadastrado."""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('Este e-mail já está cadastrado. Tente um e-mail diferente ou faça login.')

    def validate_math_answer(self, math_answer):
        """Valida a resposta da pergunta matemática."""
        # Os valores de num1 e num2 são passados no formulário como campos ocultos
        # ou podem ser armazenados na sessão se preferir não expô-los.
        # Por simplicidade, vamos assumir que eles são passados como dados do formulário.
        # A rota precisará popular form.num1.data e form.num2.data antes da validação.
        # No entanto, WTForms não preenche .data para campos ocultos da mesma forma antes da validação.
        # Uma abordagem melhor é armazenar a resposta esperada na sessão ou recalcular na validação
        # se os números originais forem passados.
        # Para este exemplo, vamos assumir que a rota irá verificar isso diretamente após form.is_submitted()
        # e antes de form.validate_on_submit() ou como parte de uma validação customizada mais complexa.

        # Abordagem mais simples: a rota irá gerar os números, passá-los para o template,
        # e também armazenar a soma esperada na sessão para verificar no POST.
        # Aqui, apenas garantimos que algo foi digitado. A lógica real da verificação
        # será na rota ou em um validador mais esperto que tenha acesso à sessão.

        # Se form.num1.data e form.num2.data fossem populados confiavelmente:
        # if self.num1.data is not None and self.num2.data is not None:
        #     expected_sum = self.num1.data + self.num2.data
        #     if math_answer.data != expected_sum:
        #         raise ValidationError('Resposta incorreta para a verificação humana.')
        # else:
        #     raise ValidationError('Erro na verificação. Tente novamente.')
        pass # A validação será feita na rota por simplicidade neste exemplo.

class LoginForm(FlaskForm):
    email = StringField('E-mail',
                        validators=[DataRequired(message="Este campo é obrigatório."),
                                    Email(message="E-mail inválido.")])
    password = PasswordField('Senha',
                             validators=[DataRequired(message="Este campo é obrigatório.")])

    # Verificação humana simples (similar ao registro)
    num1_login = IntegerField('Num1Login', render_kw={'style': 'display:none;'})
    num2_login = IntegerField('Num2Login', render_kw={'style': 'display:none;'})
    math_answer_login = IntegerField('Quanto é <span id="num1_login_display"></span> + <span id="num2_login_display"></span>?',
                                     validators=[DataRequired(message="Responda à pergunta de verificação.")])

    remember = BooleanField('Lembrar-me') # Para funcionalidade "lembrar-me" se implementada
    submit = SubmitField('Login')

# Função auxiliar para gerar números para a verificação
def generate_math_challenge():
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 9)
    return num1, num2, num1 + num2

class AdminUserActionForm(FlaskForm):
    """Formulário genérico para ações do admin que precisam de proteção CSRF."""
    # Nenhum campo visível é necessário, apenas o token CSRF implícito.
    submit = SubmitField('Executar Ação') # O texto do botão será definido no template
