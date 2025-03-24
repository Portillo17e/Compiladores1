import re

# Op relacional = <, >, =, !, <=, >=, ==, !=,
# Op lógicos = &, &&, |, ||, !
# Definir patrones de tokens
token_patron = {
    "KEYWORD": r'\b(if|else|while|for|return|int|float|void|class|def|print)\b',
    "IDENTIFIER": r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
    "NUMBER": r'\b\d+\b',
    "OPERATOR": r'<=|>=|==|!=|&&|\"|[\+\-\*/=<>\!\||\|\']',
    "DELIMITER": r'[(),;{}]',  # Paréntesis, llaves, punto y coma
    "WHITESPACE": r'\s+'  # Espacios en blanco
}


def tokenize(text):
    patron_general = "|".join(f"(?P<{token}>{patron})" for token, patron in token_patron.items())
    patron_regex = re.compile(patron_general)

    tokens_encontrados = []

    for match in patron_regex.finditer(text):
        for token, valor in match.groupdict().items():
            if valor is not None and token != "WHITESPACE":
                tokens_encontrados.append((token, valor))
    return tokens_encontrados


class NodoAST:
    def traducir(self):
        raise NotImplementedError("Método traducir no implementado en este nodo")
    
    def generar_codigo(self):
        raise NotImplementedError("Método generar_codigo no implementado en este nodo")

class NodoIf(NodoAST):
    def __init__(self, condicion, cuerpo, sino=None):
        self.condicion = condicion
        self.cuerpo = cuerpo
        self.sino = sino

    def generar_codigo(self):
        etiqueta_else = f'etiqueta_else_{id(self)}'
        etiqueta_fin = f'etiqueta_fin_{id(self)}'

        codigo = []
        codigo.append(self.condicion.generar_codigo())
        codigo.append('   cmp eax, 0 ; Comparar resultado con 0')

        operadores_salto = {
            '==': 'je',
            '!=': 'jne',
            '<': 'jl',
            '<=': 'jle',
            '>': 'jg',
            '>=': 'jge'
        }
        
        operador = self.condicion.operador[1] if hasattr(self.condicion, 'operador') else '=='
        salto = operadores_salto.get(operador, 'je')
        
        if self.sino:
            codigo.append(f'   {salto} {etiqueta_else} ; Saltar a else si la condición es falsa')
        else:
            codigo.append(f'   {salto} {etiqueta_fin} ; Saltar al final si la condición es falsa')

        for instruccion in self.cuerpo:
            codigo.append(instruccion.generar_codigo())

        if self.sino:
            codigo.append(f'   jmp {etiqueta_fin} ; Saltar al final del if')
            codigo.append(f'{etiqueta_else}:')
            for instruccion in self.sino:
                codigo.append(instruccion.generar_codigo())

        codigo.append(f'{etiqueta_fin}:')
        return '\n'.join(codigo)

# Agregar clases adicionales necesarias para completar el analizador
class NodoCondicion(NodoAST):
    def __init__(self, izquierda, operador, derecha):
        self.izquierda = izquierda
        self.operador = operador
        self.derecha = derecha

    def generar_codigo(self):
        codigo = []
        codigo.append(self.izquierda.generar_codigo())
        codigo.append('   push eax ; Guardar operando izquierdo')
        codigo.append(self.derecha.generar_codigo())
        codigo.append('   pop ebx ; Recuperar operando izquierdo')
        codigo.append('   cmp ebx, eax ; Comparar los operandos')
        return '\n'.join(codigo)

class NodoNumero(NodoAST):
    def __init__(self, valor):
        self.valor = valor
    
    def generar_codigo(self):
        return f'   mov eax, {self.valor[1]} ; Cargar número {self.valor[1]} en eax'

class NodoIdentificador(NodoAST):
    def __init__(self, nombre):
        self.nombre = nombre

    def generar_codigo(self):
        return f'   mov eax, {self.nombre[1]} ; Cargar variable {self.nombre[1]} en eax'
