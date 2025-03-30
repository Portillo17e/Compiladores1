import re
from nodos import *
import json

# === Analisis Lexico ===
# Definir los patrones para los diferentes tipos de tokens
token_patron = {
    "KEYWORD": r'\b(if|else|while|switch|case|return|print|break|for|int|float|void|double|char)\b',
    "IDENTIFIER": r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
    "NUMBER": r'\b\d+(\.\d+)?\b',
    "OPERATOR": r'[\+\-\*\/\=\<\>\!\_]',
    "DELIMITER": r'[(),;{}]',
    "WHITESPACE": r'\s+',
    "STRING": r'"[^"]*"',  
}

def identificar_tokens(texto):
    # Unir todos los patrones en un unico patron realizando grupos nombrados
    patron_general = "|".join(f"(?P<{token}>{patron})" for token, patron in token_patron.items())
    patron_regex = re.compile(patron_general)
    tokens_encontrados = []
    for match in patron_regex.finditer(texto):
        for token, valor in match.groupdict().items():
            if valor is not None and token != "WHITESPACE":
                tokens_encontrados.append((token, valor))
    return tokens_encontrados

# === Analizador Sintactico ===
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.funciones = []

    def obtener_token_actual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def coincidir(self, tipo_esperado):
        token_actual = self.obtener_token_actual()
        if token_actual and token_actual[0] == tipo_esperado:
            self.pos += 1
            return token_actual
        else:
            raise SyntaxError(f'Error sintactico: se esperaba {tipo_esperado}, pero se encontro: {token_actual}')

    def parsear(self):
        # Punto de entrada del analizador sintactico: se espera una o mas funciones
        funciones = []
        while self.pos < len(self.tokens):
            funcion = self.funcion()
            funciones.append(funcion)

        # Verificar que exista al menos una funcion 'main'
        existe_main = any(funcion.nombre == 'main' for funcion in funciones)
        if not existe_main:
            raise SyntaxError("Error sintactico: Debe existir una funcion 'main' en el codigo.")

        # Verificar que la ultima funcion sea 'main'
        if funciones[-1].nombre != 'main':
            raise SyntaxError("Error sintactico: La funcion 'main' debe ser la ultima en el codigo.")

        return NodoPrograma(funciones)  # Devolver un nodo Programa
    
    def llamada_funcion(self):
        """Procesa una llamada a funcion, como `suma(4, 3)` o `condicional(valor)`."""
        nombre_funcion = self.coincidir('IDENTIFIER')
        self.coincidir('DELIMITER')  # Consumir '('
        argumentos = self.argumentos()
        self.coincidir('DELIMITER')  # Consumir ')'

        return NodoLlamadaFuncion(nombre_funcion[1], argumentos)
    
    def argumentos(self):
        """
        Procesa los argumentos de una llamada a funcion.
        """
        argumentos = []
        while self.obtener_token_actual() and self.obtener_token_actual()[1] != ')':  # Mientras no se cierre el parentesis
            argumentos.append(self.expresion_ing())  # Analizar la expresion
            if self.obtener_token_actual() and self.obtener_token_actual()[1] == ',':
                self.coincidir('DELIMITER')  # Consumir la coma
        return argumentos
    
    def funcion(self):
        # Gramatica para una funcion: KEYWORD IDENTIFIER ( PARAMETROS ) { CUERPO }
        tipo_retorno = self.coincidir('KEYWORD')  # Tipo de retorno (ej. int)
        nombre_funcion = self.coincidir('IDENTIFIER')  # Nombre de la funcion
        self.coincidir('DELIMITER')  # Se espera un '('
        parametros = self.parametros()  # Analizar los parametros
        self.coincidir('DELIMITER')  # Se espera un ')'
        self.coincidir('DELIMITER')  # Se espera un '{'
        cuerpo = self.cuerpo()  # Analizar el cuerpo de la funcion
        self.coincidir('DELIMITER')  # Se espera un '}'
        return NodoFuncion(nombre_funcion[1], parametros, cuerpo)

    def parametros(self):
        parametros = []
        # Reglas para parametros: KEYWORD IDENTIFIER (, KEYWORD IDENTIFIER)*
        while self.obtener_token_actual() and self.obtener_token_actual()[1] != ')':  # Mientras no se cierre el parentesis
            tipo = self.coincidir('KEYWORD')  # Tipo del parametro (ej. int)
            nombre = self.coincidir('IDENTIFIER')  # Nombre del parametro (ej. a)
            parametros.append(NodoParametro(tipo[1], nombre[1]))  # Guardar el tipo y nombre
            if self.obtener_token_actual() and self.obtener_token_actual()[1] == ',':
                self.coincidir('DELIMITER')  # Consumir la coma
        return parametros

    def declaracion(self):
        tipo = self.coincidir('KEYWORD')  # Tipo de dato (ej. 'int')
        nombre = self.coincidir('IDENTIFIER')  # Nombre de la variable

        # Manejar asignacion opcional
        if self.obtener_token_actual() and self.obtener_token_actual()[1] == '=':
            self.coincidir('OPERATOR')  # Consumir '='
            # Puede ser una expresion o una llamada a funcion
            if self.obtener_token_actual()[0] == 'IDENTIFIER' and \
            self.tokens[self.pos + 1][1] == '(':
                expresion = self.llamada_funcion()
            else:
                expresion = self.expresion_ing()
            nodo = NodoAsignacion(nombre, expresion)
        else:
            nodo = NodoDeclaracion(tipo[1], nombre[1])

        self.coincidir('DELIMITER')  # Consumir ';'
        return nodo

    def asignacion(self):
        # Gramatica para el cuerpo: return IDENTIFIER OPERATOR IDENTIFIER;
        tipo = self.coincidir('KEYWORD') # tipo
        nombre = self.coincidir('IDENTIFIER') # Identificador <nombre de la variable>
        self.coincidir('OPERATOR') # Operador ej. =
        expresion = self.expresion_ing()
        self.coincidir('DELIMITER') # ;
        return NodoAsignacion(nombre, expresion)

    def retorno(self):
        self.coincidir('KEYWORD') # return
        expresion = self.expresion_ing()
        self.coincidir('DELIMITER') # ;
        return NodoRetorno(expresion)

    def cuerpo(self):
        instrucciones = []  
        while self.obtener_token_actual() and self.obtener_token_actual()[1] != '}':
            token_actual = self.obtener_token_actual()

            if token_actual[0] == 'DELIMITER' and token_actual[1] == ';':
                self.coincidir('DELIMITER')
                continue

            if token_actual[0] == 'KEYWORD':
                if token_actual[1] == 'if':
                    instrucciones.append(self.bucle_if())
                elif token_actual[1] == 'print':
                    instrucciones.append(self.printf_llamada())
                elif token_actual[1] == 'return':
                    instrucciones.append(self.retorno())
                elif token_actual[1] in ['int', 'float', 'void', 'double', 'char']:
                    # Es una declaracion (posiblemente con inicializacion)
                    instrucciones.append(self.declaracion())
                else:
                    raise SyntaxError(f'Error sintactico: Keyword no reconocido: {token_actual}')

            elif token_actual[0] == 'IDENTIFIER':
                siguiente_token = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
                if siguiente_token and siguiente_token[1] == '(':
                    # Es una llamada a funcion
                    llamada = self.llamada_funcion()
                    # Verificar si es una asignacion (ej: resultado = funcion())
                    if self.obtener_token_actual() and self.obtener_token_actual()[1] == '=':
                        self.coincidir('OPERATOR')
                        nombre = token_actual
                        instrucciones.append(NodoAsignacion(nombre, llamada))
                    else:
                        instrucciones.append(llamada)
                elif siguiente_token and siguiente_token[1] == '=':
                    # Es una asignacion simple
                    nombre = self.coincidir('IDENTIFIER')
                    self.coincidir('OPERATOR')
                    expresion = self.expresion_ing()
                    self.coincidir('DELIMITER')
                    instrucciones.append(NodoAsignacion(nombre, expresion))
                else:
                    raise SyntaxError(f'Error sintactico: Identificador no seguido de asignacion o llamada: {token_actual}')

            elif token_actual[0] in ['NUMBER', 'STRING']:
                instrucciones.append(self.expresion_ing())
                self.coincidir('DELIMITER')

            else:
                raise SyntaxError(f'Error sintactico: se esperaba una declaracion valida, pero se encontro: {token_actual}')

        return instrucciones

    def expresion_ing(self):
        izquierda = self.termino()  # Obtener el primer termino
        while self.obtener_token_actual() and self.obtener_token_actual()[0] == 'OPERATOR':
            operador = self.coincidir('OPERATOR')
            derecha = self.termino()
            izquierda = NodoOperacion(izquierda, operador[1], derecha)
        return izquierda

    def termino(self):
        token = self.obtener_token_actual()
        
        # Manejar números negativos
        if token[0] == 'OPERATOR' and token[1] == '-':
            self.coincidir('OPERATOR')  # Consumir el '-'
            numero = self.coincidir('NUMBER')
            # Crear un nodo número con valor negativo
            return NodoNumero(('NUMBER', '-' + numero[1]))
        
        if token[0] == 'NUMBER':
            return NodoNumero(self.coincidir('NUMBER'))
        elif token[0] == 'IDENTIFIER':
            return NodoIdentificador(self.coincidir('IDENTIFIER'))
        elif token[0] == 'STRING':
            return NodoString(self.coincidir('STRING'))
        else:
            raise SyntaxError(f'Error sintactico: Termino no valido {token}')
            
    def expresion(self):
        """
        Analiza expresiones matematicas o de concatenacion, por ejemplo:
        - x + y * 2
        - "hola" + nombre
        """
        if self.obtener_token_actual()[0] in ['IDENTIFIER', 'NUMBER', 'STRING']:
            self.coincidir(self.obtener_token_actual()[0])  # Consumir identificador, numero o cadena
        else:
            raise SyntaxError(f"Error sintactico: Se esperaba IDENTIFIER, NUMBER o STRING, pero se encontro {self.obtener_token_actual()}")

        while self.obtener_token_actual() and self.obtener_token_actual()[0] in ['OPERATOR']:
            self.coincidir('OPERATOR')  # Consumir operador
            if self.obtener_token_actual()[0] in ['IDENTIFIER', 'NUMBER', 'STRING']:
                self.coincidir(self.obtener_token_actual()[0])  # Consumir identificador, numero o cadena
            else:
                raise SyntaxError(f"Error sintactico: Se esperaba IDENTIFIER, NUMBER o STRING despues de {self.obtener_token_anterior()}")

    def bucle_if(self):
        """
        Analiza la estructura de una sentencia if-else if-else.
        """
        self.coincidir('KEYWORD')  # Se espera un if
        self.coincidir('DELIMITER')  # Se espera un (
        
        condicion = self.expresion_logica()
        
        self.coincidir('DELIMITER')  # Se espera un )
        self.coincidir('DELIMITER')  # Se espera un {
        
        cuerpo_if = self.cuerpo()
        
        self.coincidir('DELIMITER')  # Se espera un }
        
        cuerpo_else = None
        else_ifs = []
        
        while self.obtener_token_actual() and self.obtener_token_actual()[1] == 'else':
            self.coincidir('KEYWORD')  # Se espera un else
            
            # Verificar si es un else if
            if self.obtener_token_actual() and self.obtener_token_actual()[1] == 'if':
                self.coincidir('KEYWORD')  # Se espera un if
                self.coincidir('DELIMITER')  # Se espera un (
                
                condicion_else_if = self.expresion_logica()
                
                self.coincidir('DELIMITER')  # Se espera un )
                self.coincidir('DELIMITER')  # Se espera un {
                
                cuerpo_else_if = self.cuerpo()
                
                self.coincidir('DELIMITER')  # Se espera un }
                
                else_ifs.append((condicion_else_if, cuerpo_else_if))
            else:
                # Es un else simple
                self.coincidir('DELIMITER')  # Se espera un {
                cuerpo_else = self.cuerpo()
                self.coincidir('DELIMITER')  # Se espera un }
                break  # No puede haber mas else o else if despues de un else
        
        return NodoIf(condicion, cuerpo_if, cuerpo_else, else_ifs)

    def expresion_logica(self):
        """
        Analiza expresiones logicas y devuelve un NodoComparacion.
        """
        izquierda = None
        operador = None
        derecha = None
        
        # Manejar signo negativo si existe
        negativo = False
        if self.obtener_token_actual()[0] == 'OPERATOR' and self.obtener_token_actual()[1] == '-':
            negativo = True
            self.coincidir('OPERATOR')
        
        # Obtener el operando izquierdo
        if self.obtener_token_actual()[0] == 'IDENTIFIER':
            izquierda = NodoIdentificador(self.coincidir('IDENTIFIER'))
        elif self.obtener_token_actual()[0] == 'NUMBER':
            num = self.coincidir('NUMBER')
            if negativo:
                izquierda = NodoNumero(('NUMBER', '-' + num[1]))
                negativo = False
            else:
                izquierda = NodoNumero(num)
        else:
            raise SyntaxError(f"Error sintactico: Se esperaba IDENTIFIER o NUMBER, pero se encontro {self.obtener_token_actual()}")

        # Obtener el operador
        operador = self.coincidir('OPERATOR')[1]
        
        # Manejar operadores compuestos (==, !=, >=, <=)
        if self.obtener_token_actual()[0] == 'OPERATOR':
            segundo_op = self.coincidir('OPERATOR')[1]
            operador += segundo_op
        
        # Obtener el operando derecho
        if self.obtener_token_actual()[0] == 'IDENTIFIER':
            derecha = NodoIdentificador(self.coincidir('IDENTIFIER'))
        elif self.obtener_token_actual()[0] == 'NUMBER':
            derecha = NodoNumero(self.coincidir('NUMBER'))
        else:
            raise SyntaxError(f"Error sintactico: Se esperaba IDENTIFIER o NUMBER, pero se encontro {self.obtener_token_actual()}")

        return NodoComparacion(izquierda, operador, derecha)

    def printf_llamada(self):
        """
        Maneja las llamadas a printf como:
        printf("Mensaje", variable);
        printf(variable);
        """
        self.coincidir('KEYWORD')  # Se espera un printf
        self.coincidir('DELIMITER')  # Se espera (

        # Se espera una cadena o un identificador como primer argumento
        token_actual = self.obtener_token_actual()
        if token_actual[0] == 'STRING' or token_actual[0] == 'IDENTIFIER':
            self.coincidir(token_actual[0])  # Se espera una cadena o un identificador
        else:
            raise SyntaxError(f"Error sintactico: Se esperaba STRING o IDENTIFIER, pero se encontro {token_actual}")

        # Puede haber mas argumentos separados por comas
        while self.obtener_token_actual() and self.obtener_token_actual()[1] == ',':
            self.coincidir('DELIMITER')  # Se espera un ,
            self.expresion()  # Puede ser un identificador o numero

        self.coincidir('DELIMITER')  # Se espera un )
        self.coincidir('DELIMITER')  # Se espera un ;

    def bucle_for(self):
        # Regla para el for KEYWORD DELIMITER DECLARACION EXPRESION_LOGICA DELIMITER INCREMENT DELIMITER DELIMITER
        """
        Maneja la estructura de un bucle for.
        """
        self.coincidir('KEYWORD')  # Se espera un for
        self.coincidir('DELIMITER')  # Se espera un (

        self.declaracion() 

        self.expresion_logica() 
        self.coincidir('DELIMITER')  # Se espera un ;

        self.operador_abreviado() 
        # self.coincidir('DELIMITER')  # Se espera un )

        if self.obtener_token_actual()[0] == 'KEYWORD':
            self.cuerpo()
        else:
            self.coincidir('DELIMITER')  # Se espera un {
            self.cuerpo()  
            self.coincidir('DELIMITER')  # Se espera un }

    def return_statement(self):
        self.coincidir('KEYWORD')
        self.expresion()
        self.coincidir('DELIMITER')


    def break_statement(self):
        """
        Maneja la sentencia break.
        """
        self.coincidir('KEYWORD')  # Se espera un break
        self.coincidir('DELIMITER')  # Se espera un ;

    def operador_abreviado(self):
        self.coincidir('IDENTIFIER')
        operador_actual1 = self.obtener_token_actual()
        self.coincidir('OPERATOR')
        operador_actual2 = self.obtener_token_actual()
        self.coincidir('OPERATOR')
        if operador_actual1[1] + operador_actual2[1] not in ['++','--', '+=', '-=', '*=', '/=']:
            raise SyntaxError(f'Error sintactico: se esperaba una declaracion valida, pero se encontro: {operador_actual1[1],operador_actual2[1]}')
        self.coincidir('DELIMITER')

    def bucle_while(self):
        # Regla para bucle while: KEYWORD DELIMITER EXPRESION_LOGICA DELIMITER DELIMITER CUERPO DELIMITER
        self.coincidir('KEYWORD') # Se espera un while
        self.coincidir('DELIMITER') # Se espera un (
        self.expresion_logica()
        self.coincidir('DELIMITER') # Se espera un )
        self.coincidir('DELIMITER') # Se espera un {
        #self.printf_llamada() 
        #self.increment()
        self.cuerpo()
        self.coincidir('DELIMITER')# Se espera un }

# === Ejemplo de Uso ===
codigo_fuente = """
int condicional(int x) {
    if (x > 0) {
        return 1;
    } else if (x < 0) {
        return -1;
    } else {
        return 0;
    }
}

void main() {
    int valor = 5;
    int resultado = condicional(valor);
}
"""

# Analisis lexico
tokens = identificar_tokens(codigo_fuente)
print("Tokens encontrados:")
for tipo, valor in tokens:
    print(f'{tipo}: {valor}')

# Analisis Sintactico
try:
    print('\nIniciando analisis sintactico...')
    parser = Parser(tokens)
    arbol_ast = parser.parsear()
    print('Analisis sintactico completado sin errores')

except SyntaxError as e:
    print(e)
    
def imprimir_ast(nodo):
    if isinstance(nodo, NodoPrograma):
        return {
            "Programa": [imprimir_ast(f) for f in nodo.funciones] 
        }
    elif isinstance(nodo, NodoFuncion):
        return {
            "Funcion": nodo.nombre,
            "Parametros": [imprimir_ast(p) for p in nodo.parametros],
            "Cuerpo": [imprimir_ast(c) for c in nodo.cuerpo]
        }
    elif isinstance(nodo, NodoParametro):
        return {
            "Parametro": nodo.nombre,
            "Tipo": nodo.tipo
        }
    elif isinstance(nodo, NodoAsignacion):
        return {
            "Asignacion": nodo.nombre,
            "Expresion": imprimir_ast(nodo.expresion)
        }
    elif isinstance(nodo, NodoOperacion):
        return {
            "Operacion": nodo.operador,
            "Izquierda": imprimir_ast(nodo.izquierda),
            "Derecha": imprimir_ast(nodo.derecha)
        }
    elif isinstance(nodo, NodoRetorno):
        return {
            "Retorno": imprimir_ast(nodo.expresion)
        }
    elif isinstance(nodo, NodoIdentificador):
        return {
            "Identificador": nodo.nombre
        }
    elif isinstance(nodo, NodoNumero):
        return {
            "Numero": nodo.valor
        }
    elif isinstance(nodo, NodoLlamadaFuncion):
        return {
            "LlamadaFuncion": nodo.nombre,
            "Argumentos": [imprimir_ast(arg) for arg in nodo.argumentos]
        }
    return {}

parser = Parser(tokens)
arbol_ast = parser.parsear()    
print(json.dumps(imprimir_ast(arbol_ast), indent=1))


# nodo_exp = NodoOperacion(NodoNumero(5), '+', NodoNumero(8))
# print("Expresion original:", nodo_exp)

# exp_opt = nodo_exp.optimizar()
# print("Expresion optimizada:", exp_opt)

# codigo_python = arbol_ast.traducir()
# print(codigo_python)

codigo_asm = arbol_ast.generar_codigo()
print(codigo_asm)