import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Building2, Users, FileText, Check, ArrowRight, Loader2 } from 'lucide-react';
import { setOnboardingCompleted } from '@/shared/lib/onboarding';
import { propertiesApi } from '@/features/properties/api';
import { tenantsApi } from '@/features/tenants/api';
import { contractsApi } from '@/features/contracts/api';
import { Button } from '@/shared/ui/Button';
import { Card } from '@/shared/ui/Card';

interface Step {
  id: number;
  title: string;
  description: string;
  icon: React.ReactNode;
  actionLabel: string;
  actionPath: string;
  isCompleted: boolean;
}

interface OnboardingWizardProps {
  onComplete: () => void;
}

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [isExiting, setIsExiting] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);

  const { data: properties } = useQuery({
    queryKey: ['properties'],
    queryFn: () => propertiesApi.getAll(),
    refetchInterval: 5000,
  });
  const { data: tenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => tenantsApi.getAll(),
    refetchInterval: 5000,
  });
  const { data: contracts } = useQuery({
    queryKey: ['contracts'],
    queryFn: () => contractsApi.getAll(),
    refetchInterval: 5000,
  });

  const hasProperties = (properties?.items.length ?? 0) > 0;
  const hasTenants = (tenants?.items.length ?? 0) > 0;
  const hasContracts = (contracts?.items.length ?? 0) > 0;

  useEffect(() => {
    if (hasContracts) setCurrentStep(4);
    else if (hasTenants) setCurrentStep(3);
    else if (hasProperties) setCurrentStep(2);
    else setCurrentStep(1);
  }, [hasProperties, hasTenants, hasContracts]);

  useEffect(() => {
    if (hasProperties && hasTenants && hasContracts) {
      setIsExiting(true);
      setTimeout(() => {
        setOnboardingCompleted();
        onComplete();
      }, 500);
    }
  }, [hasProperties, hasTenants, hasContracts, onComplete]);

  const steps: Step[] = [
    {
      id: 1,
      title: 'Добавьте первый объект недвижимости',
      description: 'Квартира, дом или коммерческое помещение — всё, что вы сдаёте в аренду.',
      icon: <Building2 className="h-8 w-8" />,
      actionLabel: 'Добавить объект',
      actionPath: '/properties',
      isCompleted: hasProperties,
    },
    {
      id: 2,
      title: 'Добавьте арендатора',
      description: 'Укажите имя, контакты — они понадобятся для договоров аренды.',
      icon: <Users className="h-8 w-8" />,
      actionLabel: 'Добавить арендатора',
      actionPath: '/tenants',
      isCompleted: hasTenants,
    },
    {
      id: 3,
      title: 'Создайте договор аренды',
      description: 'Свяжите объект и арендатора, укажите сумму и срок аренды.',
      icon: <FileText className="h-8 w-8" />,
      actionLabel: 'Создать договор',
      actionPath: '/contracts',
      isCompleted: hasContracts,
    },
  ];

  const handleAction = (step: Step) => {
    if (isNavigating) return;
    setIsNavigating(true);
    setTimeout(() => {
      navigate(step.actionPath);
      setIsNavigating(false);
    }, 300);
  };

  const handleSkip = () => {
    setIsExiting(true);
    setTimeout(() => {
      setOnboardingCompleted();
      onComplete();
    }, 500);
  };

  const allCompleted = hasProperties && hasTenants && hasContracts;

  return (
    <AnimatePresence>
      {!isExiting && !allCompleted && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.4 }}
        >
          <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200 mb-6">
            <div className="flex items-center gap-2 mb-4">
              {steps.map((step) => (
                <div key={step.id} className="flex items-center gap-2 flex-1">
                  <motion.div
                    animate={{ scale: step.id === currentStep ? 1.1 : 1 }}
                    className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-all duration-500 ${
                      step.isCompleted ? 'bg-green-500 text-white' :
                      step.id === currentStep ? 'bg-blue-600 text-white' :
                      'bg-gray-200 text-gray-500'
                    }`}
                  >
                    {step.isCompleted ? <Check className="h-4 w-4" /> : step.id}
                  </motion.div>
                  <div className={`flex-1 h-1 rounded transition-all duration-500 ${
                    step.isCompleted ? 'bg-green-500' : 'bg-gray-200'
                  }`} />
                </div>
              ))}
              <motion.div
                animate={{ scale: allCompleted ? 1.1 : 1 }}
                className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium transition-all duration-500 ${
                  allCompleted ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-500'
                }`}
              >
                {allCompleted ? <Check className="h-4 w-4" /> : <Check className="h-4 w-4 opacity-30" />}
              </motion.div>
            </div>

            <motion.div
              key={currentStep}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.3 }}
              className="text-center py-4"
            >
              <div className="flex justify-center mb-4 text-blue-600">
                {steps[currentStep - 1].isCompleted ? (
                  <Check className="h-8 w-8 text-green-500" />
                ) : (
                  steps[currentStep - 1].icon
                )}
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                {steps[currentStep - 1].isCompleted
                  ? `Шаг ${currentStep} выполнен!`
                  : steps[currentStep - 1].title}
              </h3>
              <p className="text-gray-600 mb-6 max-w-md mx-auto">
                {steps[currentStep - 1].isCompleted
                  ? 'Отлично! Переходим к следующему шагу.'
                  : steps[currentStep - 1].description}
              </p>
              <div className="flex justify-center gap-3">
                {!steps[currentStep - 1].isCompleted && (
                  <Button
                    onClick={() => handleAction(steps[currentStep - 1])}
                    rightIcon={<ArrowRight className="h-4 w-4" />}
                    isLoading={isNavigating}
                  >
                    {steps[currentStep - 1].actionLabel}
                  </Button>
                )}
                {steps[currentStep - 1].isCompleted && (
                  <div className="flex items-center gap-2 text-green-600">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span className="text-sm">Ожидаем обновления...</span>
                  </div>
                )}
                <Button variant="ghost" onClick={handleSkip}>
                  Пропустить
                </Button>
              </div>
            </motion.div>
          </Card>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
